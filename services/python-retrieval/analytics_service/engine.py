# -*- coding: utf-8 -*-
"""确定性分析引擎：把五个节点按硬编码顺序串起来，全程挂链路追踪。

**流程骨架由 Python 锁死，模型只在 Node A（意图二分类）与 Node D（归因叙事）
内部充当语义单元** —— 聚合维度、占比算法、建议条目全部固化在代码与词表里。

执行的每一步都落在 Trace 上；节点异常不向上抛，记录后降级继续，
保证一次失败不会让整条链路没有观测数据。
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from rag_pipeline.observability.tracer import (KIND_GATE, STATUS_INTERCEPTED,
                                               print_trace_dashboard, Tracer)

from . import config as cfg
from .contract import (INTENT_ANALYTICS, INTENT_BLOCKED, INTENT_CLARIFY,
                       INTENT_NOT_ANALYTICS, SEVERITY_BLOCK, SEVERITY_WARN, VERDICT_ANSWERED,
                       VERDICT_CLARIFY, VERDICT_REFUSED, VERDICT_TO_REPLY_TYPE, AnalyticsState)
from .data_source import DataSource, HttpDataSource
from .model_client import ModelClient
from .nodes import (WorkflowContext, aggregate_facts, output_gate, route_intent,
                    scan_tickets, _synthesize)

DEFAULT_USER_ID = ""
DEFAULT_ROLE = "ENGINEER"


class AnalyticsWorkflow:
    """一次运行一条链路；数据源与模型可注入（测试与接入都靠这个口子）。"""

    def __init__(self, ds: Optional[DataSource] = None, model: Optional[ModelClient] = None,
                 taxonomy: Any = None):
        # 默认走 ticket-service 的只读投影扫描接口；**不直连数据库**（架构 8.1）。
        self.ds = ds
        self.model = model if model is not None else ModelClient()
        self.taxonomy = taxonomy

    # ---------------------------------------------------------------- 主入口

    def run(self, question: str, user_id: str = DEFAULT_USER_ID,
            role: str = DEFAULT_ROLE, request_id: str = "",
            upstream_intent: str = "") -> Dict[str, Any]:
        """跑完整条链路：A →（短路）→ B → C → D → E，全程写入同一棵 Trace。

        `upstream_intent`：Java 侧分类器已判定的意图。传来 ANALYTICS 时 Node A
        只跑安全闸与槽位提取，不重复调模型。
        """
        question = (question or "").strip()
        rid = request_id or uuid.uuid4().hex

        tracer = Tracer(
            trace_id=f"trace-{uuid.uuid4().hex[:12]}",
            name="TicketAnalytics-adhoc",
            workflow="跨工单宏观聚合归纳",
            user_id=user_id or "anonymous",
            session_id=f"sess-{uuid.uuid4().hex[:6]}",
        )
        # 数据源按运行时身份构造，让 X-User-Id / X-User-Role / X-Request-Id 透传到下游
        ds = self.ds or HttpDataSource(user_id=user_id, role=role, request_id=rid)
        ctx = WorkflowContext(ds=ds, model=self.model, tracer=tracer,
                              taxonomy=self.taxonomy, upstream_intent=upstream_intent)
        state = AnalyticsState(question=question, user_id=user_id, role=role, request_id=rid)

        # ===== Node A 意图路由 [ROUTER] =====
        ok = self._step("A_Intent_Router", route_intent, state, ctx)

        # 路由节点本身挂了、且没给出任何意图：不硬闯分析链路，如实说明并让上游走原链路。
        if not ok and state.intent != INTENT_ANALYTICS:
            state.intent = INTENT_NOT_ANALYTICS
            state.verdict = VERDICT_ANSWERED
            state.add_finding("ROUTER_FAILED", "意图路由异常，未进入分析链路",
                              severity=SEVERITY_WARN)

        if state.intent != INTENT_ANALYTICS:
            # 短路出口：越权拒答 / 需澄清 / 非分析型。
            # **只要不是 ANALYTICS 就不取数、不聚合、不调叙事模型** —— 非分析型请求
            # 若还跑完聚合，用户问"我 VPN 连不上怎么办"就会收到一份季度统计报告，
            # 那正是我要用仲裁压住的"答非所问"。
            self._short_circuit(state, tracer)
        else:
            # ===== Node B 投影扫描取数 [SPAN] =====
            self._step("B_Projection_Scan", scan_tickets, state, ctx)

            # ===== Node C 确定性聚合 [EVALUATOR] ★零模型调用 =====
            self._step("C_Deterministic_Aggregate", aggregate_facts, state, ctx)

            # ===== Node D 归因叙事 [GENERATION] 唯一一处模型调用 =====
            self._step("D_Answer_Narrative", _synthesize, state, ctx)

            # ===== Node E 输出门禁 [GATE] =====
            self._step("E_Output_Gate", output_gate, state, ctx)

        # ---- 链路收口 ----
        # 走到这里 verdict 理应有值；为空说明中间某步整个没跑成（异常降级等）。
        if not state.verdict:
            state.verdict = VERDICT_CLARIFY
            state.answer_text = state.answer_text or (
                "系统在处理这条分析请求时遇到异常，请稍后重试或直接联系 IT 服务台。")
        if not state.reply_type:
            state.reply_type = VERDICT_TO_REPLY_TYPE.get(state.verdict, "ANSWER")
        tracer.finish()
        return self._response(state, tracer)

    # ---------------------------------------------------------------- 内部

    def _step(self, label: str, node: Callable[[AnalyticsState, WorkflowContext], None],
              state: AnalyticsState, ctx: WorkflowContext) -> bool:
        """跑一个节点；异常已被节点自身的 span 记为 FAILED，这里只负责降级继续。

        取舍：节点抛异常时**不中断**整条链路 —— 这样单点失败不会把这次请求变成
        "一个没有任何观测数据的 500"。
        """
        try:
            node(state, ctx)
            return True
        except Exception as e:  # noqa: BLE001 —— 单节点失败不得让整条链路无观测
            state.errors.append(f"{label}: {type(e).__name__}: {e}")
            return False

    def _short_circuit(self, state: AnalyticsState, tracer: Tracer) -> None:
        """Node A 就地终局：越权拒答 / 需澄清 / 非分析型。

        这是链路的短路出口，**不取数、不聚合、不调叙事模型** —— 因此 Trace 上
        只有 2 个 span，与完整路径的 5 个形成直观对比。
        """
        reason = state.refusal_reason or state.intent
        blocked = [f.code for f in state.findings if f.severity == "BLOCK"]
        with tracer.span("A.Short_Circuit", kind=KIND_GATE) as span:
            span.record(
                input={"intent": state.intent},
                output={"action": "ABORTED", "reason": reason, "blockedBy": blocked},
                status=STATUS_INTERCEPTED,
                detail={"note": "Node A 短路返回；未取数、未聚合、未调用叙事模型"})
        if state.intent == INTENT_NOT_ANALYTICS:
            # 不是分析型请求：本链路不下结论，交回上游的既有问答链路。
            # replyType=NOT_ANALYTICS 是给 Java 侧的路由信号 —— 它据此回退走原 ragPipeline。
            state.refusal_reason = None
            state.verdict = VERDICT_ANSWERED
            state.reply_type = "NOT_ANALYTICS"
            state.confidence = 0.0
            if not state.answer_text:
                state.answer_text = ("这条请求不属于跨工单统计分析，已交由常规问答链路处理。")
        elif state.verdict == VERDICT_CLARIFY:
            state.reply_type = "CLARIFY"
            state.confidence = 0.5
        else:
            state.reply_type = "REFUSE"
            state.confidence = 0.0
            if not state.answer_text:
                reasons = "；".join(f.message for f in state.findings
                                   if f.severity == SEVERITY_BLOCK)
                state.answer_text = (
                    f"这个请求不能自动处理：{reasons}。" if reasons
                    else "这条分析请求无法处理，请稍后重试或联系 IT 服务台。")

    def _response(self, state: AnalyticsState, tracer: Tracer) -> Dict[str, Any]:
        """链路出口：把最终 state 摊平成响应，并附完整 Trace 摘要。

        `analyticsFacts` 是**带外字段** —— 与 consultation 的 `ticketDraft` 同构。
        前端表格读它，不读模型写的 `answerText`，于是"模型编造一个假的 42%"在结构上
        不可能：它能改的只有措辞。
        """
        return {
            "success": True,
            "question": state.question,
            "intent": state.intent,
            "verdict": state.verdict,
            "replyType": state.reply_type,
            "refusalReason": state.refusal_reason,
            "answerText": state.answer_text,
            "confidence": state.confidence,
            "degradedReason": state.degraded_reason,
            "scope": state.scope_domains,
            "window": state.window.as_dict() if state.window else None,
            "analyticsFacts": state.facts.as_dict() if state.facts else None,
            "findings": [f.to_dict() for f in state.findings],
            "errors": state.errors,
            "trace": tracer.summary(),
        }


def run_once(question: str, role: str = DEFAULT_ROLE) -> Dict[str, Any]:
    """便捷入口（CLI 演示用）。"""
    return AnalyticsWorkflow().run(question, role=role)


def print_dashboard(result: Dict[str, Any]) -> None:
    """终端大盘：与 HTTP 响应同一份 trace 数据，不存在两套口径。"""
    print_trace_dashboard(result.get("trace") or {})