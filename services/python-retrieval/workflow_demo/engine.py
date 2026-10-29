# -*- coding: utf-8 -*-
"""确定性工作流引擎：把四个节点按硬编码顺序串起来，并全程挂上链路追踪。

**流程骨架由 Python 锁死，模型只在 Node 1 / Node 3 内部充当语义单元** ——
这正是项目自己的原则「模型只把已有文本说得更顺，不决定发生什么」，
也是 Day17 讲义第一篇的军规。

执行的每一步都落在 Trace 上；节点异常不向上抛，记录后降级继续，
保证一次失败不会让整条链路没有观测数据。
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from . import config as cfg
from .cases import DEMO_CASES, get_case
from .contract import (INTENT_UNSUPPORTED, VERDICT_NEEDS_INFO, VERDICT_REFUSED,
                       VERDICT_TO_REPLY_TYPE, WorkflowState)
from .data_source import DataSource, SqliteDataSource
from .model_client import ModelClient
from .nodes import OFF_TOPIC_TEXT, WorkflowContext, action_gate, evaluate_and_synthesize, fork_join, route_intent
from .tracer import KIND_GATE, STATUS_INTERCEPTED, Tracer

DEFAULT_USER_ID = "U_EMP01"
DEFAULT_ROLE = "EMPLOYEE"


class DeterministicWorkflow:
    """一次运行一条链路；数据源与模型可注入（测试与接入都靠这个口子）。"""

    def __init__(self, ds: Optional[DataSource] = None, model: Optional[ModelClient] = None,
                 duplicate_window_hours: int = cfg.DUPLICATE_WINDOW_HOURS,
                 top_k: int = cfg.RETRIEVAL_TOP_K):
        self.ds = ds or SqliteDataSource()
        self.model = model if model is not None else ModelClient()
        self.duplicate_window_hours = duplicate_window_hours
        self.top_k = top_k

    # ---------------------------------------------------------------- 主入口
    def run(self, question: str, user_id: str = DEFAULT_USER_ID,
            role: str = DEFAULT_ROLE, case_id: str = "") -> Dict[str, Any]:
        """跑完整条链路：Node1 →（是否短路）→ Node2 → Node3 → Node4，全程写入同一棵 Trace。

        执行顺序在下面硬编码，不在数据里配置 —— 链路本身可预测，可预测才可审计。
        """
        question = (question or "").strip()

        # ---- 链路起点：建 Trace 根节点 ----
        # 一次 run() 一棵 Trace 树，下面每个节点/子任务都作为 span 挂在它下面。
        # 端到端时延、总 token、总成本全部以这一刻为基准（见 tracer.summary()）。
        tracer = Tracer(
            trace_id=f"trace-{uuid.uuid4().hex[:12]}",
            name=f"ITServiceDesk-{case_id or 'adhoc'}",
            workflow="IT 服务台确定性工作流",
            user_id=user_id or DEFAULT_USER_ID,
            session_id=f"sess-{uuid.uuid4().hex[:6]}",
        )
        # ctx：链路全程不变的外部依赖（数据源 / 模型 / 追踪器），各节点共享同一个实例。
        ctx = WorkflowContext(ds=self.ds, model=self.model, tracer=tracer,
                              duplicate_window_hours=self.duplicate_window_hours, top_k=self.top_k)
        # state：跨节点递进的**唯一**数据载体，也就是 Prompt Chaining 里的那条「链」。
        # 节点之间不互相调用，全部靠读写 state 字段衔接 —— 谁写、谁读，就是这条链路的实际拓扑。
        state = WorkflowState(question=question, user_id=user_id or DEFAULT_USER_ID, role=role)

        # ===== Node 1 意图路由 [ROUTER]（模式 2 Routing）=====
        # 本步写入：state.intent（四选一）、state.refusal_reason（命中红线时为 HIGH_RISK_TOPIC）、
        #          state.findings（判定依据，随响应回传给前端做审计）。
        # 紧接着的分流判断只认这两个字段 —— Node 1 是整条链路的岔道口。
        ok = self._step("Node1_Intent_Router", route_intent, state, ctx)

        if ok and (state.intent == INTENT_UNSUPPORTED
                   or state.refusal_reason == "HIGH_RISK_TOPIC"):
            # 短路：越界请求与红线操作都在 Node 1 就地返回，
            # 不进并行扇出、不碰知识库与工单 —— 省下来的就是路由分流与前置安全闸的收益
            self._refuse_short_circuit(state, tracer)
        else:
            if not ok:
                # 路由节点本身挂了：不中断链路，按最保守的知识问答路径继续往下走。
                state.errors.append("意图路由失败，按知识问答兜底")

            # ===== Node 2 并行扇出与汇聚 [PARALLEL_TASK]（模式 3 Parallelization）=====
            # 本步写入：state.knowledge（知识检索命中）、state.my_tickets（本人工单）。
            # 这两份数据就是 Node 3 做分类裁决、拼事实包的全部输入 —— 链路的第二环。
            self._step("Node2_Fork_Join", fork_join, state, ctx)

            # ===== Node 3 确定性裁决 + 模型终审 [EVALUATOR + GENERATION]（模式 4）=====
            # 读 Node 2 的两份产物，写入 state.verdict / answer_text / category_id /
            # team / priority / sla / draft —— 到这一步，链路要「发生什么」已经全部定完。
            self._step("Node3_Evaluate_Synthesize", evaluate_and_synthesize, state, ctx)

            # ===== Node 4 动作门禁 [GATE] =====
            # 链路上**唯一**产生副作用的一步：只认 state.verdict，放行分支才真的落草稿。
            self._step("Node4_Action_Gate", action_gate, state, ctx)

        # ---- 链路收口 ----
        # 走到这里 verdict 理应有值；为空说明 Node 3 整个没跑成（异常降级等）。
        # 此时给一个绝不产生副作用的兜底结论，而不是静默返回空答复。
        if state.verdict is None:
            state.verdict = VERDICT_NEEDS_INFO
            state.answer_text = state.answer_text or (
                "系统在处理这条请求时遇到异常，请稍后重试或直接联系 IT 服务台。")
        tracer.finish()   # 打上 Trace 结束时间：端到端总时延 = 起点到这一刻
        return self._response(state, tracer, case_id)   # 结论 + 完整 trace 一并返回

    def run_case(self, case_id: str, user_id: str = DEFAULT_USER_ID,
                 role: str = DEFAULT_ROLE) -> Dict[str, Any]:
        """跑演示用例：与 run() 是同一条链路，只是多带一个预期结论做对照。"""
        case = get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        result = self.run(case.question, user_id=user_id, role=role, case_id=case_id)
        # matched 是「实际 verdict vs 用例预期」，链路自检用；不参与任何业务判断。
        result["expected"] = case.expect
        result["matched"] = result["verdict"] == case.expect
        return result

    # ---------------------------------------------------------------- 内部
    def _step(self, label: str, node: Callable[[WorkflowState, WorkflowContext], None],
              state: WorkflowState, ctx: WorkflowContext) -> bool:
        """跑一个节点；异常已被节点自身的 span 记为 FAILED，这里只负责降级继续。

        链路完整性上的取舍：节点抛异常时**不中断**整条链路，继续往下走，
        后面的节点在缺失数据上做降级判断，最终仍然给员工一个答复。
        这样单点失败不会把这次请求变成「一个没有任何观测数据的 500」。
        """
        try:
            node(state, ctx)
            return True
        except Exception as e:  # noqa: BLE001 —— 单节点失败不得让整条链路无观测
            # 记进 state.errors 随响应返回；Node 3 会看到缺失的字段并走降级分支。
            state.errors.append(f"{label}: {type(e).__name__}: {e}")
            return False

    def _refuse_short_circuit(self, state: WorkflowState, tracer: Tracer) -> None:
        """Node 1 就地拒答：越界（OFF_TOPIC）或红线操作（HIGH_RISK_TOPIC），零副作用。

        这是链路的**短路出口**：从 Node 1 直接跳到终局，不经过 Node 2/3/4。
        因此这种情况下的 Trace 只有 2 个 span（1.Intent_Router + 本条），
        和非短路路径动辄 6~8 个 span 形成直观对比 —— 路由分流的收益在盘面上就是少掉的这几条。
        """
        reason = state.refusal_reason or "OFF_TOPIC"
        blocked = [f.code for f in state.findings if f.severity == "BLOCK"]
        with tracer.span("2.Safety_Refusal_FastPath", kind=KIND_GATE) as span:
            span.record(
                input={"intent": state.intent},
                output={"action": "REFUSED", "refusalReason": reason, "blockedBy": blocked},
                status=STATUS_INTERCEPTED,
                detail={"note": "Node1 前置安全闸短路返回；未执行并行扇出、未触碰知识库与工单"},
            )
        state.verdict = VERDICT_REFUSED
        state.refusal_reason = reason
        if reason == "HIGH_RISK_TOPIC":
            reasons = "；".join(f.message for f in state.findings if f.severity == "BLOCK")
            state.answer_text = (f"这个请求我不能代为处理：{reasons}。"
                                 f"请走正式流程或联系 IT 服务台人工处理。")
        else:
            state.answer_text = OFF_TOPIC_TEXT
            state.add_finding("OFF_TOPIC", "问题不属于 IT 服务范围，触发封闭世界拒答")

    def _response(self, state: WorkflowState, tracer: Tracer, case_id: str) -> Dict[str, Any]:
        """链路出口：把最终 state 摊平成 HTTP 响应，并附上完整 Trace 摘要。

        `trace` 字段就是 `Tracer.summary()` 的原样产物，所以网页端与终端大盘
        （`cli.py` → `print_trace_dashboard`）看到的是同一份数据，不存在两套口径。
        """
        trace = tracer.summary()
        return {
            "success": True,
            "caseId": case_id or None,
            "question": state.question,
            "userId": state.user_id,
            "intent": state.intent,
            "verdict": state.verdict,
            "replyType": VERDICT_TO_REPLY_TYPE.get(state.verdict, "ANSWER"),
            "refusalReason": state.refusal_reason,
            "answerText": state.answer_text,
            "usedVersionIds": state.used_version_ids,
            "categoryId": state.category_id,
            "teamId": state.team_id,
            "teamName": state.team_name,
            "priority": state.priority,
            "sla": state.sla,
            "ticketDraft": _draft_to_dict(state),
            "findings": [f.to_dict() for f in state.findings],
            "errors": state.errors,
            "trace": trace,
        }


def _draft_to_dict(state: WorkflowState) -> Optional[Dict[str, Any]]:
    if state.draft is None:
        return None
    return {
        "title": state.draft.title,
        "description": state.draft.description,
        "categoryId": state.draft.category_id,
        "priority": state.draft.priority,
        "status": "PENDING_EMPLOYEE_CONFIRM",
    }


def demo_cases() -> List[Dict[str, Any]]:
    """给前端渲染的用例清单。"""
    return [c.model_dump(by_alias=True) for c in DEMO_CASES]