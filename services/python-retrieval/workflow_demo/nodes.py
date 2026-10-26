# -*- coding: utf-8 -*-
"""四个工作流节点。每个节点是 `(state, ctx) -> None`：只读写状态对象，不返回。

- Node 1 意图路由        [ROUTER]        模式 2 Routing
- Node 2 并行扇出与汇聚   [PARALLEL_TASK] 模式 3 Parallelization
- Node 3 确定性裁决+终审  [EVALUATOR+GENERATION] 模式 4 Evaluator
- Node 4 动作门禁        [GATE]          只有门禁放行才产生副作用

约定：节点内部异常不向外抛（由 engine 统一兜底），单个节点失败不影响 Trace 落库。
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from . import config as cfg
from . import rules
from .contract import (INTENT_CREATE_TICKET, INTENT_KNOWLEDGE, INTENT_MY_TICKETS,
                       INTENT_UNSUPPORTED, VERDICT_ANSWERED, VERDICT_BLOCKED,
                       VERDICT_DRAFT_READY, VERDICT_NEEDS_INFO, VERDICT_REFUSED,
                       TicketDraft, WorkflowState)
from .data_source import DataSource
from .model_client import ModelClient, ModelUnavailable, estimate_tokens
from .tracer import (KIND_EVALUATOR, KIND_GATE, KIND_PARALLEL, KIND_ROUTER, STATUS_FAILED,
                     STATUS_INTERCEPTED, STATUS_SUCCESS, TOKENS_ESTIMATED, Tracer, brief)


@dataclass
class WorkflowContext:
    """一次运行的外部依赖：数据源 + 模型 + 追踪器。

    与 `WorkflowState` 的分工要分清，否则链路就读不懂了：
    - **ctx 是只读的、整条链路共用的** —— 一次 run() 建一份，节点只调用不修改；
    - **state 是逐节点递进的** —— 链路真正的数据载体，节点通过它衔接。
    分清之后每个节点都是 `(state, ctx) -> None` 的纯过程：读 state → 干活 → 写 state。
    """

    ds: DataSource
    model: ModelClient
    tracer: Tracer
    duplicate_window_hours: int = cfg.DUPLICATE_WINDOW_HOURS
    top_k: int = cfg.RETRIEVAL_TOP_K


# ==================================================================== Node 1 意图路由

_ROUTER_PROMPT = """你是企业 IT 服务台的意图分类器。将用户的问题归类到以下四类之一，**只输出标签本身**，不要任何解释或标点：

KNOWLEDGE_QA     —— 咨询 IT 使用方法或故障自助排查（如 VPN 连不上、打印机离线怎么办）
MY_TICKETS       —— 查询自己名下工单的状态或进度
CREATE_TICKET    —— 要求提交/创建一张工单、报修
UNSUPPORTED      —— 与 IT 服务无关（闲聊、买房、贷款、薪资等）

用户问题：{question}
标签："""


def resolve_intent(model_intent: Optional[str], rule_intent: str) -> Tuple[str, str]:
    """模型分类与规则分类的仲裁：**安全优先，规则兜底**。

    - 规则判定越界（UNSUPPORTED）时，无论模型说什么都维持越界 —— 拒答是红线，不接受模型翻案；
    - 其余情况以模型为准（语义分类是模型的强项），规则结果作为兜底与对照。
    """
    if rule_intent == INTENT_UNSUPPORTED:
        return INTENT_UNSUPPORTED, "规则判定越界，覆盖模型结果（安全优先）"
    if model_intent is None:
        return rule_intent, "模型分类不可用或无法收敛，采用规则结果"
    if model_intent == rule_intent:
        return model_intent, "模型与规则判定一致"
    return model_intent, f"模型判为 {model_intent}，规则判为 {rule_intent}，采信模型"


def route_intent(state: WorkflowState, ctx: WorkflowContext) -> None:
    """Node 1：把请求分流到不同专有子链路（Routing 模式）。

    这里的**顺序**是重点：先判红线，再决定要不要花钱调模型。
    敏感操作与越界请求都不需要模型的语义能力就能判死，先调模型再拒绝
    等于为一个注定被拦的请求付一次推理费 —— 那是 Fast-Fail 的反面。
    """
    # ===== 链路第 1 步 =====
    # 进入时 state 只有原始输入（question / user_id / role）；
    # 离开时带上 state.intent 与 state.refusal_reason —— engine 正是靠这两个字段
    # 决定这条链路是继续往 Node 2 走，还是在短路出口就地终局。
    with ctx.tracer.span("1.Intent_Router", kind=KIND_ROUTER) as span:
        span.record(input={"question": state.question})

        # (1) 规则先跑一遍。它有两个用途：无模型时的路由依据，
        #     以及模型判完之后的校验基线（不一致时会被写进 span 的 decision 里）。
        rule_intent, rule_reason = rules.rule_route(state.question)

        # (2) 前置安全闸：红线操作就地拦下。
        #     刻意放在模型调用**之前** —— 这类请求规则就能判死，模型没有翻案权
        #     （见 resolve_intent），先调模型等于为一个注定被拦的请求付一次推理费。
        sensitive = rules.guard_sensitive(state.question)
        if sensitive:
            code, message = sensitive
            state.add_finding(code, message, severity="BLOCK")
            state.refusal_reason = "HIGH_RISK_TOPIC"

        # (3) 算一下这单值不值得花钱：上一步判死的东西，直接跳过模型调用。
        skip_model = state.refusal_reason == "HIGH_RISK_TOPIC" or rule_intent == INTENT_UNSUPPORTED

        # (4) 链路上**第一处模型调用点**（另一处是 Node 3 的 _synthesize）。
        #     三条支路都会往下走，区别只在 model_intent 有没有值、token 从哪来：
        #       skip_model      → 不调，tokens_source = none
        #       模型可用         → 调，token 取服务端 usage，tokens_source = reported
        #       模型不可用/无配置 → 不调，走本地估算，tokens_source = estimated
        #     三种来源在大盘与页面上分开显示，不会被混成一个看起来同样可信的数字。
        model_intent: Optional[str] = None
        if skip_model:
            trigger = "命中红线操作" if state.refusal_reason else "规则判定越界"
            model_note = f"未调用模型：{trigger}，无需模型参与判断"
        elif ctx.model.available:
            try:
                reply = ctx.model.complete(
                    [{"role": "user", "content": _ROUTER_PROMPT.format(question=state.question)}],
                    max_tokens=cfg.ROUTER_MAX_OUTPUT_TOKENS, trace_id=ctx.tracer.trace_id)
                model_intent = rules.normalize_model_intent(reply.content)
                model_note = f"模型原始输出：{reply.content.strip()[:40]!r}"
                span.record(tokens_in=reply.tokens_in, tokens_out=reply.tokens_out,
                            tokens_source=reply.tokens_source)
            except ModelUnavailable as e:
                model_note = f"模型不可用，降级规则路由：{e}"
        else:
            # 无模型：token 由本地估算，并明确标注 estimated
            prompt = _ROUTER_PROMPT.format(question=state.question)
            span.record(tokens_in=estimate_tokens(prompt),
                        tokens_out=estimate_tokens(rule_intent),
                        tokens_source=TOKENS_ESTIMATED)

        # (5) 仲裁出最终意图，并把它写回 state —— 本节点的唯一输出。
        #     state.findings 里同时留下「规则怎么判的」，前端据此展示判定依据。
        state.intent, decision_note = resolve_intent(model_intent, rule_intent)
        state.add_finding("INTENT_ROUTE", f"意图判定为 {state.intent}：{rule_reason}")
        if state.refusal_reason == "HIGH_RISK_TOPIC":
            decision_note += "；命中敏感操作红线，短路拒答"

        # 拒答的请求，span 状态记 INTERCEPTED 而不是 FAILED ——
        # 拦下来是预期结果，不是系统出错，这两者在盘面上必须区分。
        refused = state.intent == INTENT_UNSUPPORTED or state.refusal_reason == "HIGH_RISK_TOPIC"
        span.record(
            output={"intent": state.intent, "ruleReason": rule_reason,
                    "safetyBlock": state.refusal_reason, "modelCalled": not skip_model},
            status=STATUS_INTERCEPTED if refused else STATUS_SUCCESS,
            detail={"decision": decision_note, "modelNote": model_note,
                    "ruleIntent": rule_intent},
        )


# ==================================================================== Node 2 并行扇出

def _task_knowledge(state: WorkflowState, ctx: WorkflowContext) -> None:
    """并发任务 A：检索已发布知识库（只返回 current_version_id）。

    扇出的左路。产出 state.knowledge，是 Node 3 分类裁决与事实包的第一份输入。
    """
    # 自己就是一个 span（kind=PARALLEL_TASK），与右路并发地落在同一棵 Trace 上。
    # 两条的时间区间会重叠 —— 前端甘特图正是靠 start_offset_ms 把它们画成并发条。
    with ctx.tracer.span("2.Parallel_Knowledge_RAG", kind=KIND_PARALLEL) as span:
        span.record(input={"query": state.question, "topK": ctx.top_k})
        items = ctx.ds.search_knowledge(state.question, limit=ctx.top_k)
        state.knowledge = items
        span.record(
            output={"hitCount": len(items),
                    "hits": [{"articleId": i.article_id, "versionId": i.version_id,
                              "versionNo": i.version_no, "title": i.title, "score": i.score}
                             for i in items]},
        )


def _task_my_tickets(state: WorkflowState, ctx: WorkflowContext) -> None:
    """并发任务 B：查本人工单（creator 由身份绑定，模型无法查他人）。

    扇出的右路。产出 state.my_tickets；工单查询类请求靠它出结果，
    其余路径只是顺带查一下（反正不额外花墙钟时间）。
    """
    with ctx.tracer.span("2.Parallel_My_Tickets", kind=KIND_PARALLEL) as span:
        span.record(input={"userId": state.user_id, "limit": 10})
        tickets = ctx.ds.list_my_tickets(state.user_id, limit=10)
        state.my_tickets = tickets
        span.record(
            output={"count": len(tickets),
                    "tickets": [{"ticketId": t.ticket_id, "title": t.title,
                                 "status": t.status, "priority": t.priority}
                                for t in tickets]},
        )


def fork_join(state: WorkflowState, ctx: WorkflowContext) -> None:
    """Node 2：并行扇出 + Reducer 汇聚（Parallelization 模式）。

    两路无数据依赖，墙钟耗时约为两者最大值而非之和 —— 这正是并行扇出的收益，
    大盘上的甘特条会直接显示两条并发条。
    """
    # Reducer span 包住整个 fork→join，它的 duration 就是真实的墙钟耗时。
    # 注意与两个子任务 span 的关系：Reducer 在时间轴上完整覆盖左右两路。
    with ctx.tracer.span("2.Fork_Join_Reducer", kind=KIND_PARALLEL) as span:
        span.record(input={"tasks": ["Parallel_Knowledge_RAG", "Parallel_My_Tickets"]})
        t_fork = time.perf_counter()
        # 两路一起提交、再一起收 —— 数据无依赖才敢这么写（见 docstring）。
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="wf-fork") as pool:
            f_knowledge = pool.submit(_task_knowledge, state, ctx)
            f_tickets = pool.submit(_task_my_tickets, state, ctx)
            f_knowledge.result()   # 这一行与下一行的耗时差，就是两路谁更慢
            f_tickets.result()
        wall_ms = (time.perf_counter() - t_fork) * 1000

        # 串行等效耗时 = 两路各自耗时之和。把两个数一起摆在盘面上，
        # 是为了让人看见真相：任务本身只有几毫秒时，线程池开销可能吃掉并行收益；
        # 换成真实 HTTP 数据源（几十~几百毫秒）时，并行才是净赚。
        task_ms = {s.name: s.duration_ms for s in ctx.tracer.spans}
        serial_ms = sum(v for k, v in task_ms.items() if k.startswith("2.Parallel_"))
        span.record(
            output={"syncComplete": True, "knowledgeHits": len(state.knowledge),
                    "myTickets": len(state.my_tickets)},
            detail={"serialEstimateMs": round(serial_ms, 2),
                    "parallelWallMs": round(wall_ms, 2),
                    "note": "并行墙钟应≈两路中较慢者；本地 SQLite 只有几毫秒时，"
                            "线程池开销会吃掉大部分收益，真实 HTTP 数据源才是净赚"},
        )


# ==================================================================== Node 3 裁决 + 终审

# 越界拒答文案（Node 1 短路分支与模板文案共用，保证口径一致）
OFF_TOPIC_TEXT = ("这个问题超出了 IT 服务台的处理范围。我只能答复办公 IT 相关问题"
                  "（电脑、打印机、网络、邮箱、账号、办公软件等）。")

_SYNTH_PROMPT = """你是企业 IT 服务台的答复撰写专员。下面的事实全部由系统规则算出，**不得修改、不得补充**，
也不要自己计算任何数字或判断是否合规。

要求：
- 面向员工，语气客气，**直接给结论和步骤，不要寒暄、不要复述问题**；
- 全文不超过 200 字，宁可少说也不要凑字数；
- 不要输出你的推理过程。

【规则已确定的事实】
{facts}

只输出一个 JSON 对象，不要代码块标记：
{{"answerText": "面向员工的答复正文", "usedVersionIds": ["实际依据的知识版本号，必须从下面给出的版本号中原样抄写，没有则留空数组"]}}

【可引用的知识版本号】
{versions}"""


def _build_draft(state: WorkflowState, category_id: str, priority: str) -> TicketDraft:
    """由问题文本生成草稿正文（确定性，不经模型）。"""
    question = rules.clean_text(state.question)
    title = question[:40] + ("…" if len(question) > 40 else "")
    return TicketDraft(title=title or "IT 故障报修", description=question,
                       category_id=category_id, priority=priority)


def evaluate_and_synthesize(state: WorkflowState, ctx: WorkflowContext) -> None:
    """Node 3：确定性裁决（规则层）+ 模型终审文案（生成层）。

    链路位置：Node 2 已经把 `state.knowledge` / `state.my_tickets` 填好了，
    本节点在它们之上判出 `state.verdict`，再交给 `_synthesize` 把结论写成员工读得懂的话。

    分两层是刻意的：**判定与文案分开** —— 文案写得再花哨也改不了判定结果，
    模型能碰的只有措辞，碰不到「放不放行」。
    """
    # 前半段：纯规则，一次模型调用都没有。所有 BLOCK 与 verdict 都在这里定死。
    with ctx.tracer.span("3.Deterministic_Evaluator", kind=KIND_EVALUATOR) as span:
        # 输入来自 Node 2 的并行扇出：state.knowledge（左路）、state.my_tickets（右路）。

        # ---- 分类：优先采信检索命中的高置信分类，否则走关键词规则 ----
        # 有知识命中时以检索结果为准（它带着文章的分类），没有才退回关键词表。
        rule_category, category_reason = rules.infer_category(state.question)
        top = state.knowledge[0] if state.knowledge and state.knowledge[0].score >= 0.5 else None
        category_id = top.category_id if top else rule_category
        if top:
            category_reason = f"检索命中的知识分类 {top.category_id}（{top.title}）优先于关键词规则 {rule_category}"
        state.add_finding("CATEGORY_RESOLVE", category_reason)

        # ---- 以下四项只在「建单」路径上有意义：查工单和知识问答不产生派单动作 ----
        #      每一步的结论都写进 state.findings，作为审计依据随响应回传给前端。
        duplicates: List[Any] = []
        if state.intent == INTENT_CREATE_TICKET:
            # 优先级
            state.priority, priority_reason = rules.infer_priority(state.question)
            state.add_finding("PRIORITY_RESOLVE", f"优先级 {state.priority}：{priority_reason}")

            # 支持组：查 category_route 决策表（走 SQL，不是向量检索，也不让模型猜）
            team = ctx.ds.resolve_team(category_id)
            if team:
                state.team_id, state.team_name = team
                state.add_finding("TEAM_ROUTE", f"按决策表将 {category_id} 路由至 {team[1]}（{team[0]}）")

            # SLA：查决策表。得到的是「多少秒」再加工作日历翻译成人话
            state.sla = rules.calc_sla(ctx.ds.sla_targets(), state.priority,
                                       ctx.ds.service_calendar())
            if state.sla:
                state.add_finding("SLA_TARGET",
                                  f"{state.priority} 完成 SLA {state.sla['completionTargetText']}，"
                                  f"响应 SLA {state.sla['responseTargetText']}")

            # 重复单检测：命中会在 findings 里留下 severity=BLOCK 的一条，
            # 下面的裁决段因此把它判成 BLOCKED —— 这是链路里最主要的拦截来源。
            duplicates = ctx.ds.find_open_tickets(state.user_id, category_id,
                                                  ctx.duplicate_window_hours)
            if duplicates:
                state.findings.append(rules.duplicate_finding(duplicates, ctx.duplicate_window_hours))
            else:
                state.add_finding("DUPLICATE_CHECK",
                                  f"{ctx.duplicate_window_hours} 小时内无同分类未结束工单")

        # ---- 字段完备性：描述太短没法建单，同样落一条 BLOCK ----
        too_short = len(rules.clean_text(state.question)) < 8
        if state.intent == INTENT_CREATE_TICKET and too_short:
            state.add_finding("FIELD_INCOMPLETE",
                              "问题描述过短，缺少现象/影响范围，无法建单", severity="BLOCK")

        # ---- 裁决（纯规则，模型不参与）----
        # 到这一步 severity=BLOCK 的只可能是重复单或字段不全 —— 敏感操作已在 Node 1 拦下。
        # 判定顺序即优先级：先看字段全不全，再看有没有别的 BLOCK，都没有才放行。
        blocked = [f for f in state.findings if f.severity == "BLOCK"]
        if state.intent == INTENT_CREATE_TICKET:
            if any(f.code == "FIELD_INCOMPLETE" for f in blocked):
                # 信息不足不是违规，正解是把问题问清楚，而不是拒答
                state.verdict = VERDICT_NEEDS_INFO
            elif blocked:
                state.verdict = VERDICT_BLOCKED
                state.refusal_reason = "POLICY_BLOCKED"
            else:
                # 唯一会产出草稿的分支。草稿只是内存对象，落库要等 Node 4 放行。
                state.verdict = VERDICT_DRAFT_READY
                state.draft = _build_draft(state, category_id, state.priority)
        elif state.intent == INTENT_KNOWLEDGE and not state.knowledge:
            # 没检索到依据也要答，但必须如实说明「这不是公司规定」
            state.verdict = VERDICT_ANSWERED
            state.add_finding("NO_KNOWLEDGE_HIT",
                              "知识库无命中，只能给通用排查建议，不得声称依据公司规定")
        else:
            state.verdict = VERDICT_ANSWERED

        # 本节点对外的主要产出就是 verdict；category_id 一并写回，供下游与响应使用。
        state.category_id = category_id
        # 把这个节点的判定过程整段落到 span 上（含全部 findings），
        # 于是「为什么是这个结论」在链路里是可回溯的，而不只是一个结果。
        span.record(
            input={"intent": state.intent, "question": state.question},
            output={"verdict": state.verdict, "categoryId": category_id,
                    "teamId": state.team_id, "priority": state.priority,
                    "findings": [f.to_dict() for f in state.findings]},
            detail={"note": "全部数字与判定由 Python 规则算出，见 findings"},
        )

    # 后半段：进入生成层。verdict 已经定死，这里只负责把结论说成员工读得懂的话。
    _synthesize(state, ctx)


def _facts_block(state: WorkflowState) -> Dict[str, Any]:
    """交给模型的事实包：全部是已算好的结论，模型只做转述。

    这里是**「确定性 → 生成」的交接边界**：跨过它之后，数字、分类、SLA、依据
    都已经是既成事实，模型能自主决定的只剩措辞。提示词里那句「不得修改、不得补充」
    靠的就是这个包的结构 —— 模型手上根本没有原始数据，只有结论。
    """
    facts: Dict[str, Any] = {"意图": state.intent, "裁决": state.verdict,
                             "优先级": state.priority, "规则依据": [f.message for f in state.findings]}
    if state.team_name:
        facts["承办支持组"] = f"{state.team_name}（{state.team_id}）"
    if state.sla:
        facts["完成SLA"] = state.sla["completionTargetText"]
        facts["响应SLA"] = state.sla["responseTargetText"]
    if state.knowledge:
        facts["检索到的知识"] = [{"标题": k.title, "版本": f"v{k.version_no}",
                                  "版本号": k.version_id, "摘要": k.summary} for k in state.knowledge]
    else:
        facts["检索到的知识"] = "无（不得声称依据公司规定或内部知识）"
    if state.my_tickets:
        facts["本人名下工单"] = [{"单号": t.ticket_id, "标题": t.title,
                                  "状态": t.status, "优先级": t.priority} for t in state.my_tickets]
    return facts


# 降级原因：链路上要能区分「模型没调」「调了但异常」「调了但输出不可用」，
# 否则排查时只看到一句「答复是模板」，猜不出到底哪一环出的问题。
DEGRADED_TRUNCATED = "MODEL_TRUNCATED"           # 撞上 max_tokens，JSON 被砍断
DEGRADED_UNPARSABLE = "MODEL_OUTPUT_UNPARSABLE"  # 结构不符，解析不出正文


def _fallback_text(state: WorkflowState) -> str:
    """无模型时的模板文案：只复述规则结论，措辞固定、可预期。

    链路的降级出口，_synthesize 的四条支路里有三条会落到这里
    （无模型 / 模型失败 / 模型输出不可用）。
    分支顺序与 verdict 的语义一一对应，加分支时要跟着 contract 里的枚举一起改。
    """
    if state.verdict == VERDICT_REFUSED:
        return OFF_TOPIC_TEXT
    if state.verdict == VERDICT_BLOCKED:
        reasons = "；".join(f.message for f in state.findings if f.severity == "BLOCK")
        return f"这个请求不能自动处理：{reasons}。已建议转人工复核。"
    if state.verdict == VERDICT_NEEDS_INFO:
        return ("信息还不够，请补充：具体现象、开始时间、影响范围（是否影响办公）、"
                "以及设备资产编号，我再帮你建单。")
    if state.intent == INTENT_MY_TICKETS:
        if not state.my_tickets:
            return "你名下目前没有工单记录。"
        lines = [f"你名下有 {len(state.my_tickets)} 张工单："]
        for t in state.my_tickets:
            lines.append(f"- {t.ticket_id}｜{t.title}｜状态 {t.status}｜优先级 {t.priority}")
        return "\n".join(lines)
    if state.verdict == VERDICT_DRAFT_READY and state.draft:
        return (f"已为你整理好工单草稿：{state.draft.title}\n"
                f"承办支持组：{state.team_name}；优先级：{state.priority}；"
                f"完成 SLA：{state.sla.get('completionTargetText', '-')}。\n"
                f"草稿尚未建单，请确认后提交。")
    if state.knowledge:
        top = state.knowledge[0]
        return f"根据《{top.title}》（v{top.version_no}）：\n{top.body}"
    return ("知识库中没有找到完全匹配的条目。可以先按通用方式排查：重启设备、检查网线与电源、"
            "确认账号状态；若仍无法恢复，请提交工单并附上具体现象。"
            "以上为通用 IT 建议，不代表公司内部规定。")


def _synthesize(state: WorkflowState, ctx: WorkflowContext) -> None:
    """模型终审：把已定的事实写成员工读得懂的话，并做引用守卫。

    链路上**第二处、也是最后一处模型调用点**。四条出口，都不能改变 verdict：
    - 无模型        → 用确定性模板文案（`_fallback_text`），token 标记 estimated；
    - 模型调用失败   → 同样退回模板文案，span 记 FAILED，链路照走；
    - 模型成功       → 取文案，但引用的版本号必须过 `rules.verify_citation` 守卫；
    - 成功但输出不可用 → 退回模板文案，span 记 FAILED，保留原始输出与降级原因。
    """
    # 先备好模板文案：降级分支直接用，不必等到出错再临时拼。
    fallback = _fallback_text(state)
    # generation span：kind=GENERATION，大盘上按它统计「模型调用次数」。
    with ctx.tracer.generation("3.Answer_Synthesis", model=cfg.LLM_MODEL) as gen:
        gen.record(input={"verdict": state.verdict, "intent": state.intent})

        if not ctx.model.available:
            # 出口 1：没配模型。用模板文案，但 token 仍如实标注为 estimated ——
            # 「没调模型」和「调了但没回 usage」是两回事，盘面上不合并统计。
            facts = _facts_block(state)
            prompt = _SYNTH_PROMPT.format(facts=json.dumps(facts, ensure_ascii=False),
                                          versions=state.knowledge and
                                          [k.version_id for k in state.knowledge] or [])
            gen.record(output={"answerText": fallback}, tokens_in=estimate_tokens(prompt),
                       tokens_out=estimate_tokens(fallback), tokens_source=TOKENS_ESTIMATED,
                       detail={"mode": "template", "note": "未配置模型，使用确定性模板文案"})
            state.answer_text = fallback
            state.used_version_ids = [k.version_id for k in state.knowledge]
            return   # 出口 1 结束：链路继续往 Node 4 走

        # 出口 2/3 共用：把本次真正检索到的版本号列入白名单，
        # 模型只能从这份清单里挑，挑不出别的（引用守卫的依据就是这个 versions）。
        versions = [k.version_id for k in state.knowledge]
        prompt = _SYNTH_PROMPT.format(
            facts=json.dumps(_facts_block(state), ensure_ascii=False),
            versions=json.dumps(versions, ensure_ascii=False))
        try:
            reply = ctx.model.complete([{"role": "user", "content": prompt}],
                                       max_tokens=cfg.SYNTH_MAX_OUTPUT_TOKENS,
                                       trace_id=ctx.tracer.trace_id)
        except ModelUnavailable as e:
            # 出口 2：模型挂了。退回模板文案并把 span 记为 FAILED，
            # 但链路不中断 —— 员工照样拿得到一个（保守的）答复。
            gen.record(status=STATUS_FAILED, error=str(e),
                       output={"answerText": fallback, "degraded": True},
                       detail={"mode": "template-fallback", "note": f"模型失败降级：{e}"})
            state.answer_text = fallback
            state.used_version_ids = versions
            return

        # 出口 3/4 共用：解析模型输出。拿不出正文就走出口 4 降级 —— 见 _parse_synthesis。
        text, claimed, usable = _parse_synthesis(reply.content)
        if not usable:
            # 出口 4：模型调通了、也有回包，但拿不出可用的正文。最常见的原因是
            # 推理模型：思维链先把 max_tokens 吃掉，JSON 被拦腰截断。
            # 按项目约定这不算「静默回退」—— 显式记 FAILED、把真实原因与原始输出
            # 留在链路上，员工拿到的仍是可读的模板文案，而不是半截 JSON。
            truncated = reply.finish_reason == "length"
            note = ("模型输出被 max_tokens 截断（finish_reason=length）" if truncated
                    else "模型输出中解析不出 answerText")
            gen.record(status=STATUS_FAILED, error=note,
                       output={"answerText": fallback, "degraded": True},
                       tokens_in=reply.tokens_in, tokens_out=reply.tokens_out,
                       tokens_source=reply.tokens_source,
                       detail={"mode": "template-fallback",
                               "degradedReason": DEGRADED_TRUNCATED if truncated
                               else DEGRADED_UNPARSABLE,
                               "rawOutput": brief(reply.content),
                               "note": f"{note}：已降级为模板文案"})
            state.answer_text = fallback
            state.used_version_ids = versions
            return

        # 出口 3：模型给出了可用正文。文案照收，但引用必须过守卫 ——
        # 模型声称依据的版本号只要不在本次检索结果里，就当场剔除并记一条 finding。
        kept, dropped = rules.verify_citation(claimed, state.knowledge)
        if dropped:
            state.add_finding("CITATION_REJECTED",
                              f"模型声称依据 {dropped}，但本次检索并未返回这些版本，已剔除",
                              severity="INFO")
        state.used_version_ids = kept
        state.answer_text = text   # 链路上最终面向员工的那段话，在这里定稿
        gen.record(output={"answerText": text, "usedVersionIds": kept,
                           "rejectedVersionIds": dropped},
                   tokens_in=reply.tokens_in, tokens_out=reply.tokens_out,
                   tokens_source=reply.tokens_source,
                   detail={"mode": "model"})


def _parse_synthesis(content: str) -> Tuple[str, List[str], bool]:
    """解析模型输出的 JSON，返回 `(正文, 引用, 是否可用)`。

    **拿不出正文时 ok=False，绝不把原始文本当答复回传。** 推理模型的输出一旦被
    max_tokens 截断，回传的就是半截 JSON（`{"answerText": "…`）—— 那是模型内部
    协议的碎片，不是给员工看的话。旧实现的 `return raw` 正是把这段残片直接送给了
    员工，页面上看着像乱码，链路里还记着 SUCCESS。
    """
    raw = (content or "").strip()
    if not raw:
        return "", [], False
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.strip()
    try:
        payload = json.loads(raw)
    except ValueError:
        return "", [], False
    if not isinstance(payload, dict):
        return "", [], False
    text = str(payload.get("answerText") or "").strip()
    if not text:
        # 结构对但正文为空：同样是「拿不出正文」，交给调用方降级，
        # 不要返回半成品字符串让下游去猜。
        return "", [], False
    used = [v for v in (payload.get("usedVersionIds") or []) if isinstance(v, str)]
    return text, used, True


# ==================================================================== Node 4 动作门禁

def action_gate(state: WorkflowState, ctx: WorkflowContext) -> None:
    """Node 4：按裁决执行副作用。只有放行分支才真正动作，拦截分支零副作用。

    链路最后一站，也是整条链路上**唯一**会改变外部世界的一步。
    它只读 `state.verdict`（Node 3 定的），不看模型写了什么 ——
    所以模型再怎么措辞，都推不动这道闸。
    """
    with ctx.tracer.span("4.Action_Gate", kind=KIND_GATE) as span:
        span.record(input={"verdict": state.verdict})
        if state.verdict == VERDICT_DRAFT_READY and state.draft:
            # 放行：落草稿。注意也只是「草稿」—— 真正建单要员工在 Java 侧确认。
            draft = ctx.ds.create_draft(state.user_id, state.draft)
            span.record(output={"action": "DRAFT_CREATED", "draft": draft})
        elif state.verdict in (VERDICT_BLOCKED, VERDICT_REFUSED):
            # 拦截：验的是「零副作用」。span 状态记 INTERCEPTED，
            # 与 FAILED 区分开 —— 拦下来是这条链路正常工作的证明，不是故障。
            span.record(
                output={"action": "ABORTED", "refusalReason": state.refusal_reason,
                        "blockedBy": [f.code for f in state.findings if f.severity == "BLOCK"]},
                status=STATUS_INTERCEPTED,
                detail={"note": "门禁拦截，未产生任何副作用（未建单、未落库）"},
            )
        else:
            # 只读答复（知识问答 / 查工单）：本来就无事可做，如实记 NONE。
            span.record(output={"action": "NONE", "note": "只读答复，无副作用"})