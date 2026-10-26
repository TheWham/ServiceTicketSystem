# -*- coding: utf-8 -*-
"""五个节点。每个节点是 `(state, ctx) -> None`：只读写状态对象，不返回。

- Node A 分析意图路由     [ROUTER]        模型主判 + 规则兜底 + 安全闸
- Node B 投影扫描取数     [SPAN]          只按时间窗，不做子域粗筛
- Node C 确定性聚合       [EVALUATOR]     零模型调用 ★核心
- Node D 归因叙事         [GENERATION]    唯一一处模型调用
- Node E 输出门禁         [GATE]          数字与单号守卫

约定：节点内部异常不向外抛（由 engine 统一兜底），单个节点失败不影响 Trace 落库。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from rag_pipeline.observability.tracer import (KIND_EVALUATOR, KIND_GATE, KIND_GENERATION,
                                               KIND_ROUTER, KIND_SPAN, STATUS_FAILED,
                                               STATUS_INTERCEPTED, STATUS_SUCCESS,
                                               TOKENS_ESTIMATED, STATUS_SKIPPED, Tracer, brief)

from . import config as cfg
from . import rules
from .classifier import (CLARIFY_TEXT, classify_with_model, resolve_analytics_intent,
                         rule_route)
from .contract import (DEGRADED_CALL_FAILED, DEGRADED_NO_MODEL, DEGRADED_TRUNCATED,
                       DEGRADED_UNPARSABLE, GATE_SMALL_UNIVERSE, INTENT_ANALYTICS,
                       INTENT_BLOCKED, INTENT_CLARIFY, INTENT_NOT_ANALYTICS,
                       REFUSAL_MODEL_UNAVAILABLE, REFUSAL_NO_RELIABLE_KNOWLEDGE,
                       REFUSAL_POLICY_BLOCKED, SEVERITY_BLOCK, SEVERITY_INFO, SEVERITY_WARN,
                       SOURCE_MODEL, VERDICT_ANSWERED, VERDICT_CLARIFY, VERDICT_REFUSED,
                       VERDICT_TO_REPLY_TYPE, AnalyticsState, Recommendation, parse_narrative)
from .data_source import DataSource, ScanError
from .model_client import ModelClient, ModelUnavailable, estimate_tokens
from .timewindow import parse_window


@dataclass
class WorkflowContext:
    """一次运行的外部依赖：数据源 + 模型 + 追踪器。

    `ctx` 是只读的、整条链路共用的；`state` 是逐节点递进的、链路真正的数据载体。
    """

    ds: DataSource
    model: ModelClient
    tracer: Tracer
    taxonomy: Any = None
    # 上游（Java 侧 SemanticRequestClassifier）已判定的意图。非空且为 ANALYTICS 时
    # Node A 只跑安全闸与槽位提取，**不重复调模型做二次分类** —— 那是一次白花的推理费。
    upstream_intent: str = ""


# ============================================================ Node A 意图路由

def route_intent(state: AnalyticsState, ctx: WorkflowContext) -> None:
    """Node A：判定是否走分析链路。

    **顺序是重点**：先判红线，再决定要不要花钱调模型。越权角色的请求规则就能判死，
    先调模型再拒绝等于为一个注定被拦的请求付一次推理费。
    """
    with ctx.tracer.span("A.Intent_Router", kind=KIND_ROUTER) as span:
        span.record(input={"question": state.question, "role": state.role})

        # (1) 规则先跑：无模型时的路由依据，以及模型判完之后的对照基线。
        rule_hit, rule_detail = rule_route(state.question, ctx.taxonomy)
        state.rule_intent = INTENT_ANALYTICS if rule_hit else INTENT_NOT_ANALYTICS

        # (2) 前置安全闸：跨人聚合是本链路唯一新增权限面。
        #     刻意放在模型调用**之前** —— 这类请求规则就能判死，模型没有翻案权。
        if state.role and state.role.upper() not in cfg.ALLOWED_ROLES:
            state.intent = INTENT_BLOCKED
            state.refusal_reason = REFUSAL_POLICY_BLOCKED
            state.verdict = VERDICT_REFUSED
            state.add_finding(
                "ROLE_DENIED",
                f"角色 {state.role} 无权调用跨工单分析（仅限 "
                f"{'/'.join(sorted(cfg.ALLOWED_ROLES))}）", severity=SEVERITY_BLOCK)
            span.record(output={"intent": INTENT_BLOCKED, "refusalReason": state.refusal_reason},
                        status=STATUS_INTERCEPTED,
                        detail={"decision": "命中原权限闸，未调用模型"})
            return

        # (3) 上游已指定意图或规则明确命中时，不重复调模型做二次分类
        #     —— Java 侧 SemanticRequestClassifier 已经判过一次了。
        upstream_intent = ctx.upstream_intent or ""
        skip_model = rule_hit or upstream_intent == INTENT_ANALYTICS
        model_intent: Optional[str] = None
        tokens: Dict[str, Any] = {"tokens_source": "none"}

        if skip_model:
            model_note = ("上游已指定为分析型请求，跳过二次分类" if upstream_intent == INTENT_ANALYTICS
                          else "规则明确命中分析型信号，跳过模型分类")
        else:
            model_intent, model_note, tokens = classify_with_model(
                ctx.model, state.question, trace_id=ctx.tracer.trace_id)
            state.model_intent = model_intent

        # (4) 仲裁出最终意图。走到这里的 skip_model 分支必然是分析型
        #     （规则命中 或 上游已认定），无需再仲裁。
        if skip_model:
            state.intent = INTENT_ANALYTICS
            decision_note = "规则/上游已定性，直接进入分析链路"
        else:
            state.intent, decision_note = resolve_analytics_intent(model_intent, rule_hit)

        # (5) 澄清出口：模型判为分析但规则没背书 —— 跨服务边界误判代价高，先问一句
        if state.intent == INTENT_CLARIFY:
            state.verdict = VERDICT_CLARIFY
            state.answer_text = CLARIFY_TEXT
            state.add_finding("CLARIFY_NEEDED", decision_note, severity=SEVERITY_WARN)
            span.record(output={"intent": state.intent}, status=STATUS_SUCCESS,
                        detail={"decision": decision_note, "modelNote": model_note,
                                "ruleIntent": rule_detail, **tokens})
            return

        state.add_finding("INTENT_ROUTE", f"意图判定为 {state.intent}：{rule_detail}")
        span.record(
            output={"intent": state.intent, "ruleIntent": state.rule_intent,
                    "modelIntent": state.model_intent, "modelCalled": not skip_model},
            status=STATUS_SUCCESS,
            detail={"decision": decision_note, "modelNote": model_note,
                    "ruleDetail": rule_detail, **tokens})


# ============================================================ Node B 取数

def scan_tickets(state: AnalyticsState, ctx: WorkflowContext) -> None:
    """Node B：投影扫描取数。

    **只按时间窗过滤，不传 category** —— 子域过滤 100% 交给 Node C 的词表。
    实测算过：若在这一层按 `category IN ('C_NET','C_HW_PR')` 粗筛，那张
    `category_id = C_HW_PC` 的打印机工单在数据库层就被滤掉，根本活不到 Node C。
    """
    with ctx.tracer.span("B.Projection_Scan", kind=KIND_SPAN) as span:
        window = parse_window(state.question)
        state.window = window
        span.record(input={"createdAfter": window.start_iso,
                           "createdBefore": window.end_iso,
                           "windowSource": window.source})
        try:
            rows = ctx.ds.scan_tickets(window, category="")
        except ScanError as e:
            # 取数与"没查到"是两回事：**不用模型通用知识替代**，如实拒答。
            state.verdict = VERDICT_REFUSED
            state.refusal_reason = REFUSAL_MODEL_UNAVAILABLE
            state.add_finding("SCAN_FAILED", f"工单取数失败：{e}", severity=SEVERITY_BLOCK)
            span.record(status=STATUS_FAILED, error=str(e))
            return
        state.tickets = rows
        span.record(output={"scanned": len(rows),
                            "note": "代理失败与空结果是两回事，此处仅在失败时降级"})


# ============================================================ Node C 确定性聚合

def aggregate_facts(state: AnalyticsState, ctx: WorkflowContext) -> None:
    """Node C：确定性聚合（**零模型调用**）。

    这里产出的每个数字都是代码算的。跨过这一步之后，模型能自主决定的只剩措辞。
    """
    from . import aggregate as agg
    from . import taxonomy as tx

    with ctx.tracer.span("C.Deterministic_Aggregate", kind=KIND_EVALUATOR) as span:
        if state.verdict == VERDICT_REFUSED:
            span.record(status=STATUS_SKIPPED, detail={"note": "取数失败，跳过聚合"})
            return

        tax = ctx.taxonomy or tx.load_taxonomy()
        scope_domains = tx.resolve_domains(state.question, tax)
        state.scope_domains = [d.name for d in scope_domains]

        t0 = time.perf_counter()
        facts = agg.build_facts(state.tickets, state.window, scope_domains, tax)
        state.facts = facts
        cost_ms = (time.perf_counter() - t0) * 1000

        # 逐条闸门进 findings —— 结论必须可解释，不能只给一个数字
        for g in facts.gates:
            state.add_finding(g.code, g.message, severity=g.severity)

        span.record(
            input={"scanned": len(state.tickets), "scope": state.scope_domains,
                   "window": facts.window},
            output={"universe": facts.universe,
                    "topSymptoms": [{"label": e.label, "count": e.count, "ratio": e.ratio}
                                    for d in facts.dimensions if d.axis == tx.AXIS_SYMPTOM
                                    for e in d.entries[:5]],
                    "gates": [g.code for g in facts.gates]},
            detail={"note": "全部数字由 Python 算出，模型无权修改",
                    "aggregateCostMs": round(cost_ms, 2),
                    "taxonomyVersion": tax.version, "taxonomyFingerprint": tax.fingerprint},
        )

        # 样本不足 → 诚实拒答（不是降级）：说明为何不做宏观归纳，并附实际分布
        if facts.has_block_gate():
            state.verdict = VERDICT_REFUSED
            state.refusal_reason = REFUSAL_NO_RELIABLE_KNOWLEDGE
        else:
            state.verdict = VERDICT_ANSWERED


# ============================================================ Node D 归因叙事

_SYNTH_PROMPT = """你是企业 IT 服务台的运维分析撰写人。下面的事实**全部由系统统计算出，不得修改、不得补充**，
也不要自己计算任何数字或推断任何原因。

要求：
- 面向 IT 主管，先给结论再给依据，不要寒暄、不要复述问题；
- **全文控制在 400 字以内**，宁可少说也不要凑字数。只展开占比最高的前 3 项，
  其余条目不要逐条罗列 —— 明细在页面上有表格，正文不必重复；
- 若事实里给出了「本次提问关注」，**正文必须以该维度为主展开**，其余维度一句带过。
  实测踩到过：问「共性根因是什么」，模型通篇写现象分布、根因一个字没提；
- **每一个百分比和数量都必须原样引用下面给出的事实**，不得换算、不得四舍五入到"约 XX%"以外的形式；
- 下面标注「样本不足」的条目，只能说"命中 N 单，样本不足以据此下结论"，**不得给出占比**；
- 下面标注「无法归纳」的维度，直接说明原因，不要用其他维度替代它下结论；
- 必须披露统计口径（时间范围）与标签覆盖率，以及未覆盖部分；
- 直接使用下面给出的中文字段名，不要输出任何英文字段名或等号形式的键值；
- 不要输出你的推理过程。

【系统统计出的事实】
{facts}

只输出一个 JSON 对象，不要代码块标记：
{{"answerText": "面向 IT 主管的分析正文",
  "citedTicketIds": ["正文中实际引用的工单号，必须从下面给出的样例单号中原样抄写，没有则留空数组"],
  "recommendations": [{{"text": "一条排查或巡检建议", "basisLabels": ["支撑它的统计标签，原样抄写"]}}]}}

recommendations 的要求：
- 结合上面给出的**真实统计**归纳出排查方向与巡检重点。可以对成因作合理推断
  （如"蓝屏集中在少数机型"→ 建议先做内存与驱动的一致性排查），这是本次归纳的价值所在；
- **不得写任何数量**。备件的数量已由系统按固定系数算出并列在上面，你写的数字会与它打架；
- 每条必须用 basisLabels 声明依据的是上面哪一个标签，**标签名必须原样抄写、不得新造**；
- 给 2~4 条即可，宁可少而准。

【可引用的样例单号】
{ids}"""


def _focus_axis(question: str) -> Optional[str]:
    """识别提问**明确要的是哪个维度**，用于把它排到事实包最前面。

    为什么必须做：三个维度平铺给模型、正文又有长度上限时，被问到却排在最后的那个
    维度会被整个挤掉。实测踩到过 —— 问「本季度工单的共性根因是什么？」，模型通篇写
    现象分布，**根因一个字没提**，只在一句"样本不足"里捎带了名词。答案看着完整，
    其实没回答问题。

    识别走确定性关键词，不调模型：这一步只是排序提示，判错最多让展示顺序不理想，
    不会改变任何数字。
    """
    q = question or ""
    if any(k in q for k in ("根因", "原因", "为什么坏", "为什么坏", "故障原因")):
        return AXIS_ROOT_CAUSE_LABEL
    if any(k in q for k in ("现象", "症状", "表现", "什么问题")):
        return AXIS_SYMPTOM_LABEL
    if any(k in q for k in ("设备", "机型", "硬件类型")):
        return AXIS_DEVICE_LABEL
    return None


# 事实包里维度的中文名（与 _facts_block 输出一致）
AXIS_SYMPTOM_LABEL = "故障现象分布"
AXIS_DEVICE_LABEL = "设备分布"
AXIS_ROOT_CAUSE_LABEL = "共性根因"
_AXIS_LABEL = {"SYMPTOM": AXIS_SYMPTOM_LABEL, "DEVICE": AXIS_DEVICE_LABEL,
               "ROOT_CAUSE": AXIS_ROOT_CAUSE_LABEL}


def _facts_block(state: AnalyticsState) -> Dict[str, Any]:
    """交给模型的事实包：全部是已算好的结论。

    这里是**「确定性 → 生成」的交接边界**。跨过它之后，占比、覆盖率、建议条目
    都已经是既成事实；提示词里那句"不得修改、不得补充"靠的是这个包的结构 ——
    模型手上**根本没有原始工单文本**，想编也无从编起。
    """
    facts = state.facts
    if facts is None:
        return {}

    dims: List[Dict[str, Any]] = []
    for d in facts.dimensions:
        label = _AXIS_LABEL.get(d.axis, d.axis)
        if not d.entries:
            dims.append({"维度": label, "结论": "该维度无法归纳（无可用来源）"})
            continue
        items = []
        # 只给前 4 项。实测**推理量由事实包的复杂度驱动，不是长度**：
        # 完整包（3 维 × 8 项 + 建议）要 9344 个 completion token、其中 9004 是推理、耗时 55s；
        # 精简单维只需 411 个、4s —— 差 23 倍。明细在页面上有表格，正文不需要它。
        for e in d.entries[:4]:
            row: Dict[str, Any] = {"项目": e.label, "命中单数": e.count}
            if e.ratio is not None:
                row["占本维度比例"] = f"{e.ratio}%"
                row["占全部工单比例"] = f"{e.ratio_of_all}%"
            else:
                row["占比"] = "样本不足，不给占比"
            row["样例单号"] = e.sample_ticket_ids[:2]
            items.append(row)
        dims.append({"维度": label, "分布": items})

    # 被问到的维度排最前：正文有长度上限，排在最后的维度会被整个挤掉（实测踩到过）
    focus = _focus_axis(state.question)
    if focus:
        dims.sort(key=lambda x: 0 if x.get("维度") == focus else 1)

    recs = [{"类型": r.kind, "内容": r.text} for r in facts.recommendations]

    # 全部改用中文键名。模型会照抄它在 facts 里看到的字段名 —— 实测正文里出现过
    # "标签覆盖率 ratio=100.0"、"labelled=3，total=3"、"来源规则解析" 这类把内部
    # 字段名写给主管看的情况。事实包是给模型读的，但它的**键名会变成用户可见的词**。
    return {
        "统计口径": {"范围": (facts.window or {}).get("label"),
                     "起": (facts.window or {}).get("start"),
                     "止": (facts.window or {}).get("end")},
        "范围限定": (facts.scope or {}).get("domains") or "全库（未限定范围）",
        "样本": {"时间窗内有效工单": facts.universe.get("total"),
                 "纳入统计的工单": facts.universe.get("scoped")},
        "标签覆盖率": {"覆盖率": f"{facts.coverage.ratio}%",
                       "纳入统计的工单数": facts.coverage.total,
                       "被排除的非有效工单": facts.coverage.excluded},
        "分布": dims,
        # 这块**只是备件建议**（数量由代码按固定系数算出）。排查与巡检方向不在里面 ——
        # 那部分交给模型结合上面的分布去归纳，但它无权改这里的数字。
        "备件建议（系统按固定系数算出，原样引用，不得改写数量）": recs,
        "数据限制": [g.message for g in facts.gates],
        **({"本次提问关注": focus, "要求": f"正文以「{focus}」为主展开，其余维度一句带过"}
           if focus else {}),
    }


def _sample_ids(state: AnalyticsState) -> List[str]:
    if state.facts is None:
        return []
    return sorted(state.facts.allowed_ticket_ids())[:20]


def _fallback_text(state: AnalyticsState) -> str:
    """确定性模板文案：只复述统计结论，措辞固定、可预期。

    降级出口共用。**只复述数字，不产建议** —— 无模型时系统仍要能给出可核验的
    统计结果，而不是一段读着像分析、实则无依据的话。
    """
    facts = state.facts
    lines: List[str] = []

    if state.refusal_reason == REFUSAL_POLICY_BLOCKED:
        return f"这个请求不能自动处理：{'；'.join(state.block_messages())}。已建议转人工复核。"
    if state.refusal_reason == REFUSAL_MODEL_UNAVAILABLE and facts is None:
        return ("工单数据暂时取不到，无法完成这次统计归纳。"
                "请稍后重试；如果你只是要问某个具体故障怎么处理，我可以直接答复。")
    if facts is None:
        return "本次未能取到可分析的数据。"

    win = facts.window
    scope = facts.scope or {}
    head = f"统计口径：{win.get('label')}（{win.get('start')} ~ {win.get('end')}）"
    if scope.get("applied"):
        head += f"；范围限定：{'、'.join(scope.get('domains') or [])}"
    lines.append(head + "。")

    if facts.has_block_gate():
        lines.append("；".join(facts.block_messages()) + "。")
    lines.append(f"时间窗内有效工单 {facts.universe.get('total')} 单，"
                 f"标签覆盖率 {facts.coverage.ratio}%。")

    for d in facts.dimensions:
        if not d.entries:
            continue
        parts = []
        for e in d.entries[:5]:
            parts.append(f"{e.label} {e.count} 单（{e.ratio}%）" if e.ratio is not None
                         else f"{e.label} {e.count} 单（样本不足，不出占比）")
        lines.append(f"{d.axis} 分布：" + "；".join(parts) + "。")

    excluded = facts.coverage.excluded
    if excluded:
        detail = "、".join(f"{k} {v} 单" for k, v in excluded.items())
        lines.append(f"已排除的非有效工单：{detail}。")

    for r in facts.recommendations:
        lines.append(f"[{r.kind}] {r.text}")
    return "\n".join(lines)


def _attach_suggestions(state: AnalyticsState,
                        suggestions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """把模型建议过守卫后挂到 facts 上，返回 `(保留的, 被剔除的)`。

    建议与代码算出的备件建议**同列在一张表里**，由 `source` 字段区分 ——
    前端据此分组展示：读者必须能分清哪部分是统计结论、哪部分是模型归纳。

    这里只剔除"造数"与"引用不存在标签"的条目，**不校验推断方向本身**：
    从「蓝屏集中在少数机型」推出「先查内存与驱动一致性」是归纳，是这条链路的价值所在。
    """
    if state.facts is None or not suggestions:
        return [], []
    kept, dropped = rules.verify_suggestions(suggestions, state.facts)
    for item in kept:
        state.facts.recommendations.append(Recommendation(
            kind="排查与巡检",
            text=item["text"],
            basis_label="、".join(item["basisLabels"]),
            severity=SEVERITY_INFO,
            source=SOURCE_MODEL))
    return kept, dropped


def _synthesize(state: AnalyticsState, ctx: WorkflowContext) -> None:
    """Node D：把已定的事实写成分析正文，并做引用守卫。

    四条出口，都不能改变 facts 里的任何数字与条目：
    - 无模型        → 确定性模板文案，token 标 estimated
    - 模型调用失败   → 同样退回模板文案，span 记 FAILED，链路照走
    - 模型成功       → 取文案，但数字与单号要过 `rules.verify_all` 守卫
    - 成功但输出不可用 → 退回模板文案，span 记 FAILED，保留原始输出与降级原因
    """
    fallback = _fallback_text(state)
    with ctx.tracer.generation("D.Answer_Narrative", model=cfg.LLM_MODEL) as gen:
        gen.record(input={"verdict": state.verdict,
                          "gates": [g.code for g in (state.facts.gates if state.facts else [])]})

        if state.verdict != VERDICT_ANSWERED or state.facts is None:
            # 拒答/澄清路径没有叙事环节，直接落模板（拒答文案已由 _fallback_text 给出）
            gen.record(output={"answerText": state.answer_text or fallback},
                       status=STATUS_SKIPPED,
                       detail={"mode": "template", "note": "非作答路径，不经模型叙事"})
            state.answer_text = state.answer_text or fallback
            state.reply_type = VERDICT_TO_REPLY_TYPE.get(state.verdict, "ANSWER")
            return

        if not ctx.model.available:
            facts = _facts_block(state)
            prompt = _SYNTH_PROMPT.format(facts=json.dumps(facts, ensure_ascii=False),
                                          ids=_sample_ids(state))
            gen.record(output={"answerText": fallback}, tokens_in=estimate_tokens(prompt),
                       tokens_out=estimate_tokens(fallback), tokens_source=TOKENS_ESTIMATED,
                       detail={"mode": "template", "degradedReason": DEGRADED_NO_MODEL,
                               "note": "未配置模型，使用确定性模板文案"})
            state.answer_text = fallback
            state.degraded_reason = DEGRADED_NO_MODEL
            return

        prompt = _SYNTH_PROMPT.format(
            facts=json.dumps(_facts_block(state), ensure_ascii=False),
            ids=json.dumps(_sample_ids(state), ensure_ascii=False))
        try:
            reply = ctx.model.complete([{"role": "user", "content": prompt}],
                                       max_tokens=cfg.SYNTH_MAX_OUTPUT_TOKENS,
                                       trace_id=ctx.tracer.trace_id)
        except ModelUnavailable as e:
            gen.record(status=STATUS_FAILED, error=str(e),
                       output={"answerText": fallback, "degraded": True},
                       detail={"mode": "template-fallback", "degradedReason": DEGRADED_CALL_FAILED,
                               "note": f"模型失败降级：{e}"})
            state.answer_text = fallback
            state.degraded_reason = DEGRADED_CALL_FAILED
            return

        text, claimed, suggestions, usable = parse_narrative(reply.content)
        if not usable:
            # 模型调通了、也有回包，但拿不出可用正文。最常见的原因是推理模型：
            # 思维链先把 max_tokens 吃掉，JSON 被拦腰截断。
            # 按项目约定这不算"静默回退" —— 显式记 FAILED、把真实原因与原始输出留在链路上。
            truncated = reply.finish_reason == "length"
            reason = DEGRADED_TRUNCATED if truncated else DEGRADED_UNPARSABLE
            note = ("模型输出被 max_tokens 截断（finish_reason=length）" if truncated
                    else "模型输出中解析不出 answerText")
            gen.record(status=STATUS_FAILED, error=note,
                       output={"answerText": fallback, "degraded": True},
                       tokens_in=reply.tokens_in, tokens_out=reply.tokens_out,
                       tokens_source=reply.tokens_source,
                       detail={"mode": "template-fallback", "degradedReason": reason,
                               "rawOutput": brief(reply.content),
                               "note": f"{note}：已降级为模板文案"})
            state.answer_text = fallback
            state.degraded_reason = reason
            return

        state.answer_text = text
        state.degraded_reason = None

        kept_sug, dropped_sug = _attach_suggestions(state, suggestions)
        for sug_text, reason in dropped_sug:
            # 剔除建议**不降级整条回答**：统计结论与备件建议都还在，被剔的只是
            # 模型的归纳方向。但必须留痕 —— 否则"模型给了 4 条建议却只显示 2 条"
            # 在页面上看不出任何解释。
            state.add_finding("SUGGESTION_REJECTED",
                              f"剔除一条模型建议：{reason}（原文：{sug_text[:40]}）",
                              severity=SEVERITY_WARN)

        gen.record(output={"answerText": text, "claimedTicketIds": claimed,
                           "suggestions": len(kept_sug), "rejectedSuggestions": len(dropped_sug)},
                   tokens_in=reply.tokens_in, tokens_out=reply.tokens_out,
                   tokens_source=reply.tokens_source, detail={"mode": "model"})


# ============================================================ Node E 输出门禁

def _caliber_line(facts: Any) -> str:
    """统计口径行。**由代码拼，不交给模型自觉。**

    提示词里写着"必须披露统计口径"，但实测模型会写出一段漂亮却漏掉"这是哪个时间段
    的数据"的正文 —— 而口径恰恰是结论能不能用的前提。它是**事实**，不是措辞，
    所以和占比、建议一样由代码保证。
    """
    win = (facts.window or {}) if facts else {}
    parts = [f"统计口径：{win.get('label')}（{win.get('start')} ~ {win.get('end')}）"]
    scope = (facts.scope or {}) if facts else {}
    if scope.get("applied"):
        parts.append(f"范围限定：{'、'.join(scope.get('domains') or [])}")
    return "；".join(parts) + "。"


def output_gate(state: AnalyticsState, ctx: WorkflowContext) -> None:
    """Node E：数字与单号守卫。

    模型能把 9/28 写成"约 40%"，也能顺手编一个单号。这一关把站不住脚的句子剔除；
    剔到没有内容就整体退回确定性模板 —— **宁可读起来朴素，也不给一个错数字**。
    """
    with ctx.tracer.span("E.Output_Gate", kind=KIND_GATE) as span:
        if state.verdict != VERDICT_ANSWERED or state.facts is None:
            if state.reply_type == "ANSWER":
                # 澄清等非统计作答路径，正文不经数字校验（本来就不含统计数字）
                state.reply_type = VERDICT_TO_REPLY_TYPE.get(state.verdict, state.reply_type)
                state.confidence = 0.5
            span.record(input={"verdict": state.verdict},
                        output={"action": "SKIPPED", "note": "非统计作答，无需数字门禁"},
                        status=STATUS_SKIPPED)
            return

        facts = state.facts
        original = state.answer_text or ""
        kept, dropped, ok = rules.verify_all(original, facts)

        if dropped:
            state.add_finding(
                "CLAIM_REJECTED",
                f"剔除 {len(dropped)} 处无法溯源的表述：{'；'.join(d[:40] for d in dropped[:3])}",
                severity=SEVERITY_WARN)

        if not ok:
            # 剔空 → 整体退回模板：不做局部改写，也不放行半截结论。
            state.answer_text = _fallback_text(state)
            state.degraded_reason = state.degraded_reason or DEGRADED_UNPARSABLE
            # 模型建议一并撤掉：它的正文已经证明自己在编数字，那么同一轮里给出的
            # 建议也不该继续挂在结论下面 —— 留着等于"正文判定不可信，但它的推论照用"。
            # 代码算出的备件建议不受影响（source=rule）。
            before = len(state.facts.recommendations)
            state.facts.recommendations = [r for r in state.facts.recommendations
                                           if r.source != SOURCE_MODEL]
            withdrawn = before - len(state.facts.recommendations)
            note = ("模型叙事中的数字/单号无法全部溯源，已整体退回确定性统计文案"
                    + (f"，并撤回其 {withdrawn} 条建议" if withdrawn else ""))
            state.add_finding("NARRATIVE_FALLBACK", note, severity=SEVERITY_WARN)
        else:
            state.answer_text = kept

        # 口径行由代码补：模型漏写时补上，已写时不重复。放在数字门禁之后，
        # 因为它本身不含需要校验的统计数字（只有日期）。
        window_label = (facts.window or {}).get("label") or ""
        if window_label and window_label not in state.answer_text:
            state.answer_text = _caliber_line(facts) + "\n\n" + state.answer_text

        state.reply_type = "ANSWER"
        # 置信度由闸门而非模型自称决定：有 BLOCK 闸门说明结论受限，覆盖率低要再降一档
        conf = 0.85
        if any(g.severity == SEVERITY_WARN for g in facts.gates):
            conf -= 0.15
        if facts.coverage.ratio < cfg.MIN_COVERAGE_WARN * 100:
            conf -= 0.15
        state.confidence = round(max(0.1, conf), 2)

        span.record(
            input={"length": len(original)},
            output={"droppedSentences": len(dropped), "keptLength": len(state.answer_text),
                    "confidence": state.confidence},
            status=STATUS_SUCCESS,
            detail={"note": "数字与单号必须可溯源；剔除后不足则整体退回模板"})