# -*- coding: utf-8 -*-
"""链路追踪内核：Trace → Span → Generation 三级拓扑（Langfuse 语义，零依赖本地实现）。

共享内核：workflow_demo（演示）与 agent_service（真实系统）共用本模块，
保证两边看到的链路拓扑与字段语义一致。

设计取舍（对齐 Day17 讲义但修掉其三个坑）：

1. **计时用 `time.perf_counter()`**（单调时钟）。讲义用 `time.time()`，会被系统时钟
   调整影响，测出的毫秒数不可信。
2. **Token 必须标注来源**（`reported` / `estimated` / `none`）。讲义把「模型没调、
   硬编码的 token 数」和「API 真实回传的 usage」用同样方式打印，看起来一样可信。
   这里把两者分开，页面上也分开显示。
3. **费率配置化**（`config.PRICE_*`），不硬编码。讲义写死 0.15/0.60，换个模型就全错。

字段名对齐 Langfuse 语义（traceId / spanName / totalCostUsd ...），
以后要接真 SDK 只需新增一个 Exporter，业务代码不动。
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional


import os
# 环境变量与 workflow_demo.config 同名同默认——本模块是共享内核，不反向依赖任何业务包。
_BRIEF_MAX_CHARS = int(os.environ.get("TRACE_BRIEF_MAX_CHARS", "240"))
_PRICE_INPUT_PER_M = float(os.environ.get("TRACE_PRICE_INPUT_PER_M", "0.15"))
_PRICE_OUTPUT_PER_M = float(os.environ.get("TRACE_PRICE_OUTPUT_PER_M", "0.60"))

# span 类型：ROUTER(意图路由) / PARALLEL_TASK(并行扇出子任务) / EVALUATOR(确定性裁决)
#          / GATE(动作门禁) / GENERATION(模型推理) / SPAN(其它逻辑阶段)
KIND_ROUTER = "ROUTER"
KIND_PARALLEL = "PARALLEL_TASK"
KIND_EVALUATOR = "EVALUATOR"
KIND_GATE = "GATE"
KIND_GENERATION = "GENERATION"
KIND_SPAN = "SPAN"

# 状态：SUCCESS 正常 / INTERCEPTED 被门禁拦下或短路（是预期结果，不是错误）/ FAILED 异常 / SKIPPED 未执行
STATUS_SUCCESS = "SUCCESS"
STATUS_INTERCEPTED = "INTERCEPTED"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"

# token 来源：reported=模型 API 回传 / estimated=本地估算 / none=本节点不涉模型
TOKENS_REPORTED = "reported"
TOKENS_ESTIMATED = "estimated"
TOKENS_NONE = "none"


def brief(value: Any, limit: Optional[int] = None) -> Any:
    """把 span 的输入输出压成可安全回传前端的摘要：长文本截断、dict 只保留浅层。"""
    limit = limit or _BRIEF_MAX_CHARS
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"…(+{len(value) - limit}字)"
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in list(value.items())[:12]:
            out[str(k)] = brief(v, limit) if not isinstance(v, (list, dict)) else _brief_container(v, limit)
        return out
    if isinstance(value, (list, tuple)):
        return _brief_container(value, limit)
    return str(value)[:limit]


def _brief_container(value: Any, limit: int) -> Any:
    """列表/嵌套结构：只交代规模与前两项，避免把整页 JSON 塞进响应。"""
    if isinstance(value, dict):
        return {str(k): brief(v, limit) for k, v in list(value.items())[:8]}
    items = list(value)
    head = [brief(v, limit) for v in items[:2]]
    if len(items) > 2:
        head.append(f"…共{len(items)}项")
    return head


@dataclass
class SpanRecord:
    """一个 span 的完整记录（同时供终端大盘与 web 前端渲染）。"""

    name: str
    kind: str
    status: str
    start_offset_ms: float   # 相对 trace 起点的偏移，前端据此画甘特条
    duration_ms: float
    input: Any = None
    output: Any = None
    tokens_in: int = 0
    tokens_out: int = 0
    tokens_source: str = TOKENS_NONE
    cost_usd: float = 0.0
    error: Optional[str] = None
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spanName": self.name,
            "kind": self.kind,
            "status": self.status,
            "startOffsetMs": round(self.start_offset_ms, 2),
            "durationMs": round(self.duration_ms, 2),
            "input": self.input,
            "output": self.output,
            "tokensInput": self.tokens_in,
            "tokensOutput": self.tokens_out,
            "tokensSource": self.tokens_source,
            "costUsd": round(self.cost_usd, 7),
            "error": self.error,
            "detail": self.detail,
        }


class SpanScope:
    """`with tracer.span(...) as s:` 的作用域对象；块结束时自动落库。

    span 的生命周期 = 链路上一个阶段的生命周期：`__enter__` 是阶段开始，
    `__exit__` 是阶段结束并落库。因此节点里的 `with` 块边界不是随手写的，
    它划定的就是这个阶段在甘特图上的那一段。
    """

    def __init__(self, tracer: "Tracer", name: str, kind: str):
        self._tracer = tracer
        self._name = name
        self._kind = kind
        self._start = 0.0
        self.input: Any = None
        self.output: Any = None
        self.status = STATUS_SUCCESS
        self.tokens_in = 0
        self.tokens_out = 0
        self.tokens_source = TOKENS_NONE
        self.error: Optional[str] = None
        self.detail: Dict[str, Any] = {}

    def __enter__(self) -> "SpanScope":
        # 链路进入这个阶段：记起点。用单调时钟，不受系统时间调整影响。
        self._start = time.perf_counter()
        return self

    def record(self, *, input: Any = None, output: Any = None, status: Optional[str] = None,
               tokens_in: int = 0, tokens_out: int = 0,
               tokens_source: str = TOKENS_NONE, error: Optional[str] = None,
               detail: Optional[Dict[str, Any]] = None) -> "SpanScope":
        """记录本 span 的结果；可在块内多次调用，后写的覆盖先写的。"""
        if input is not None:
            self.input = input
        if output is not None:
            self.output = output
        if status is not None:
            self.status = status
        if tokens_in:
            self.tokens_in = int(tokens_in)
        if tokens_out:
            self.tokens_out = int(tokens_out)
        if tokens_source != TOKENS_NONE:
            self.tokens_source = tokens_source
        if error:
            self.error = error
        if detail:
            self.detail.update(detail)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        # 阶段结束：算出耗时并落库。start_offset_ms 是相对 Trace 起点的偏移，
        # 前端据此把每个 span 画到甘特图的正确位置上（并发条因此会重叠）。
        duration_ms = (time.perf_counter() - self._start) * 1000
        if exc is not None:
            # 抛异常也算一个阶段：标 FAILED 并留下错误原文，观测数据不会缺一块。
            self.status = STATUS_FAILED
            self.error = self.error or f"{exc_type.__name__}: {exc}"
        self._tracer._append(
            SpanRecord(
                name=self._name,
                kind=self._kind,
                status=self.status,
                start_offset_ms=(self._start - self._tracer.started_at) * 1000,
                duration_ms=duration_ms,
                input=brief(self.input),
                output=brief(self.output),
                tokens_in=self.tokens_in,
                tokens_out=self.tokens_out,
                tokens_source=self.tokens_source if (self.tokens_in or self.tokens_out) else TOKENS_NONE,
                # 成本在落库时就算好：费率来自 config，token 来源已在上面标定，
                # 于是「这个数字可不可信」在数据结构层面就是明确的。
                cost_usd=self._tracer.cost_of(self.tokens_in, self.tokens_out),
                error=self.error,
                detail=self.detail,
            )
        )
        return False  # 不吞异常，交由工作流节点自行降级（见 engine._step）


class Tracer:
    """一次请求一棵 Trace 树；线程安全（并行扇出的两个子任务会同时写）。"""

    def __init__(self, trace_id: str, name: str, workflow: str = "",
                 user_id: str = "", session_id: str = ""):
        # 链路起点：engine.run() 一进来就建好这个对象，started_at 因此是「整条链路的 0 刻度」——
        # 所有 span 的 start_offset_ms 都相对它计算。
        self.trace_id = trace_id
        self.name = name
        self.workflow = workflow
        self.user_id = user_id
        self.session_id = session_id
        self.started_at = time.perf_counter()
        self.ended_at: Optional[float] = None
        self._spans: List[SpanRecord] = []
        self.price_input_per_m = _PRICE_INPUT_PER_M
        self.price_output_per_m = _PRICE_OUTPUT_PER_M

    # ------------------------------------------------------------ 采集
    @contextmanager
    def span(self, name: str, kind: str = KIND_SPAN) -> Iterator[SpanScope]:
        """记一个逻辑阶段（路由 / 并行子任务 / 裁决 / 门禁都走这里）。"""
        scope = SpanScope(self, name, kind)
        with scope:
            yield scope

    @contextmanager
    def generation(self, name: str, model: str = "") -> Iterator[SpanScope]:
        """模型推理节点；模型名写进 detail，便于按模型归因成本。

        与 `span()` 只差 kind 与 model 字段，但大盘靠 kind=GENERATION 统计
        「模型调用次数」—— 所以链路上真正调模型的两处（Node 1 路由、Node 3 终审）
        必须走这个方法，否则成本口径就乱了。
        """
        scope = SpanScope(self, name, KIND_GENERATION)
        scope.detail["model"] = model
        with scope:
            yield scope

    def _append(self, record: SpanRecord) -> None:
        self._spans.append(record)

    def cost_of(self, tokens_in: int, tokens_out: int) -> float:
        return (tokens_in * self.price_input_per_m + tokens_out * self.price_output_per_m) / 1_000_000

    def finish(self) -> None:
        if self.ended_at is None:
            self.ended_at = time.perf_counter()

    # ------------------------------------------------------------ 汇总
    @property
    def spans(self) -> List[SpanRecord]:
        return list(self._spans)

    def summary(self) -> Dict[str, Any]:
        """链路收口：把所有 span 汇总成一份可序列化的 Trace 摘要。

        产物同时喂给三个消费方 —— HTTP 响应的 `trace` 字段、终端大盘、
        网页甘特图 —— 三者口径一致，不存在「页面和日志对不上」的问题。
        """
        self.finish()   # 若还没结束就先封口，保证 totalLatencyMs 有值
        total_in = sum(s.tokens_in for s in self._spans)
        total_out = sum(s.tokens_out for s in self._spans)
        total_cost = sum(s.cost_usd for s in self._spans)
        generations = [s for s in self._spans if s.kind == KIND_GENERATION]
        # 真正调用过模型的节点（Token 来源非 none）。路由节点若走了模型也算在内，
        # 因为它的 token 同样计费。
        model_calls = [s for s in self._spans if s.tokens_source != TOKENS_NONE]
        slowest = max(self._spans, key=lambda s: s.duration_ms, default=None)
        costliest = max(self._spans, key=lambda s: s.cost_usd, default=None)
        return {
            "traceId": self.trace_id,
            "name": self.name,
            "workflow": self.workflow,
            "userId": self.user_id,
            "sessionId": self.session_id,
            "totalLatencyMs": round((self.ended_at - self.started_at) * 1000, 2),
            "totalTokens": total_in + total_out,
            "totalInputTokens": total_in,
            "totalOutputTokens": total_out,
            "totalCostUsd": round(total_cost, 7),
            "spanCount": len(self._spans),
            "generationCount": len(generations),
            "modelCallCount": len(model_calls),
            # 有多少节点是本地估算的 token：前端据此提示「成本为估算值」
            "estimatedSpans": sum(1 for s in model_calls if s.tokens_source == TOKENS_ESTIMATED),
            "priceInputPerM": self.price_input_per_m,
            "priceOutputPerM": self.price_output_per_m,
            "slowestSpan": slowest.to_dict() if slowest else None,
            "costliestSpan": costliest.to_dict() if costliest else None,
            "spans": [s.to_dict() for s in self._spans],
        }

    # ------------------------------------------------------------ 终端大盘
    def print_dashboard(self) -> None:
        print_trace_dashboard(self.summary())


def print_trace_dashboard(summary: Dict[str, Any]) -> None:
    """把 Trace 摘要渲染成终端 ASCII 大盘。

    接受的是 `Tracer.summary()` 的那份 dict，所以 HTTP 响应里的 `trace` 字段
    可以原样丢进来（见 `cli.py`），终端与网页看到的是同一份数据。
    """
    s = summary
    print("\n" + "=" * 104)
    print("📊 【链路追踪大盘 (Trace / Span / Generation)】")
    print("=" * 104)
    print(f"  • Trace ID     : {s['traceId']}")
    print(f"  • 工作流        : {s['workflow'] or s['name']}")
    print(f"  • 操作人/会话    : {s['userId']} / {s['sessionId']}")
    print(f"  • 端到端总时延   : {s['totalLatencyMs']} ms")
    print(f"  • 总 Token      : {s['totalTokens']} (输入 {s['totalInputTokens']} | 输出 {s['totalOutputTokens']})")
    cost_note = "（含估算）" if s["estimatedSpans"] else ""
    print(f"  • 总成本        : ${s['totalCostUsd']:.7f} USD{cost_note}")
    if s["slowestSpan"]:
        print(f"  • 最慢节点      : {s['slowestSpan']['spanName']} ({s['slowestSpan']['durationMs']}ms)")
    print("-" * 104)
    print(f"{'阶段节点':<34}{'类型':<15}{'状态':<14}{'耗时(ms)':<12}{'Token(入/出)':<16}{'成本(USD)':<12}{'Token来源'}")
    print("-" * 104)
    for sp in s["spans"]:
        tok = f"{sp['tokensInput']}/{sp['tokensOutput']}"
        print(f"{sp['spanName']:<34}{sp['kind']:<15}{sp['status']:<14}"
              f"{sp['durationMs']:<12}{tok:<16}${sp['costUsd']:<11.7f}{sp['tokensSource']}")
    print("=" * 104)