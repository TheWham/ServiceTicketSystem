# -*- coding: utf-8 -*-
"""把本地 Tracer 摘要导出到 Langfuse。

关键设计：
1. 业务代码只生成 `Tracer.summary()`，本模块负责上报。
2. 默认不上报 prompt / 知识正文 / 模型输出；只有 `LANGFUSE_INCLUDE_CONTENT=true` 才会带上
   Tracer 已经截断的 input/output。这样接 APM 时默认不引入敏感信息泄露。
3. 上报失败只记日志，不影响 AI 主链路。
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any, Dict, Optional


log = logging.getLogger(__name__)


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def _fallback_trace_id(seed: str) -> str:
    seed = seed or uuid.uuid4().hex
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def _observation_type(name: str, kind: str) -> str:
    """按 Langfuse observation type 语义选择最具体类型。"""
    if kind == "GENERATION":
        return "generation"
    suffix = name.rsplit(".", 1)[-1]
    if suffix in {"search_knowledge", "query_my_tickets"}:
        return "retriever"
    if suffix == "prepare_ticket":
        return "tool"
    if name.startswith("tool."):
        return "tool"
    return "span"


class LangfuseExporter:
    """把一次端到端请求的 Agent / Generation / Tool 树上报到 Langfuse。"""

    def __init__(self, config: Optional[Any] = None):
        from .. import config as acfg
        self.enabled = (config or acfg).LANGFUSE_ENABLED
        self.include_content = (config or acfg).LANGFUSE_INCLUDE_CONTENT
        self._client = None
        if not self.enabled:
            return
        if not (config or acfg).LANGFUSE_PUBLIC_KEY or not (config or acfg).LANGFUSE_SECRET_KEY:
            log.warning("[Langfuse] 已启用但缺少 PUBLIC_KEY / SECRET_KEY，本次请求不会上报")
            self.enabled = False
            return

        try:
            from langfuse import Langfuse
            self._client = Langfuse(
                public_key=(config or acfg).LANGFUSE_PUBLIC_KEY,
                secret_key=(config or acfg).LANGFUSE_SECRET_KEY,
                host=(config or acfg).LANGFUSE_HOST or None,
                environment=(config or acfg).LANGFUSE_ENV or None,
                timeout=max(1, int((config or acfg).LANGFUSE_TIMEOUT_SECONDS)),
            )
        except Exception as exc:  # noqa: BLE001 —— 观测上报失败不能影响业务主链路
            log.exception("[Langfuse] 客户端初始化失败: %s", type(exc).__name__)
            self.enabled = False
            self._client = None

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self._client is not None)

    def trace_id(self, seed: str = "") -> str:
        """由外部请求 ID 派生 Langfuse 可用的确定性 32-hex trace ID。"""
        if self.configured:
            try:
                return str(self._client.create_trace_id(seed=seed or None))
            except Exception:  # noqa: BLE001 —— SDK 不可用时回退本地确定性 ID
                pass
        return _fallback_trace_id(seed)

    def export(self, summary: Dict[str, Any]) -> Optional[str]:
        """上报一整棵 Agent trace；返回 Langfuse trace URL（失败返回 None）。"""
        if not self.configured or not summary:
            return None
        try:
            from langfuse import propagate_attributes
            from langfuse.types import TraceContext
            safe_input = {
                "requestId": summary.get("requestId", ""),
                "inputSha256": summary.get("inputSha256", ""),
                "materialCount": _int(summary.get("materialCount")),
                "historyTurns": _int(summary.get("historyTurns")),
                "assetIdPresent": bool(summary.get("assetIdPresent")),
            }
            safe_output = {
                "outputSha256": summary.get("outputSha256", ""),
                "usedVersionIds": list(summary.get("usedVersionIds", [])),
                "replyType": summary.get("replyType", ""),
                "confidence": summary.get("confidence", 0.0),
            }
            with self._client.start_as_current_observation(
                as_type="agent",
                name=str(summary.get("name") or "agent.chat"),
                trace_context=TraceContext(trace_id=str(summary.get("traceId"))),
                input=safe_input if not self.include_content else summary.get("input"),
                output=safe_output if not self.include_content else summary.get("output"),
                metadata={
                    "workflow": summary.get("workflow", ""),
                    "totalLatencyMs": summary.get("totalLatencyMs", 0),
                    "totalInputTokens": _int(summary.get("totalInputTokens")),
                    "totalOutputTokens": _int(summary.get("totalOutputTokens")),
                    "totalTokens": _int(summary.get("totalTokens")),
                    "totalCostUsd": summary.get("totalCostUsd", 0.0),
                    "spanCount": _int(summary.get("spanCount")),
                    "generationCount": _int(summary.get("generationCount")),
                    "modelCallCount": _int(summary.get("modelCallCount")),
                    "estimatedSpans": _int(summary.get("estimatedSpans")),
                    "priceInputPerM": summary.get("priceInputPerM", 0.0),
                    "priceOutputPerM": summary.get("priceOutputPerM", 0.0),
                },
            ) as root:
                with propagate_attributes(
                    user_id=str(summary.get("userId") or ""),
                    session_id=str(summary.get("sessionId") or "") or None,
                    tags=["agent-chat", "it-ticket"],
                ):
                    for span in summary.get("spans", []):
                        self._export_span(root, span)
            self._client.flush()
            return self._client.get_trace_url(trace_id=str(summary.get("traceId")))
        except Exception as exc:  # noqa: BLE001 —— Langfuse 不可用不能拖垮回答
            log.exception("[Langfuse] trace 上报失败: %s", type(exc).__name__)
            return None

    def _export_span(self, root: Any, span: Dict[str, Any]) -> None:
        is_generation = span.get("kind") == "GENERATION"
        name = str(span.get("spanName") or "span")
        observation_type = _observation_type(name, str(span.get("kind") or ""))
        tokens_in = _int(span.get("tokensInput"))
        tokens_out = _int(span.get("tokensOutput"))
        cost = float(span.get("costUsd") or 0.0)
        metadata = {
            "status": span.get("status", ""),
            "startOffsetMs": span.get("startOffsetMs", 0.0),
            "durationMs": span.get("durationMs", 0.0),
            "tokensInput": tokens_in,
            "tokensOutput": tokens_out,
            "tokensSource": span.get("tokensSource", "none"),
            "costUsd": cost,
            "error": span.get("error"),
            "detail": span.get("detail", {}),
        }
        kwargs: Dict[str, Any] = {
            "name": name,
            "as_type": observation_type,
            "metadata": metadata,
            "level": "ERROR" if span.get("status") == "FAILED" else "DEFAULT",
        }
        if span.get("error"):
            kwargs["status_message"] = str(span["error"])[:500]
        if is_generation:
            model = (span.get("detail") or {}).get("model") or ""
            if model:
                kwargs["model"] = str(model)
            if tokens_in or tokens_out:
                kwargs["usage_details"] = {
                    "input": tokens_in,
                    "output": tokens_out,
                    "total": tokens_in + tokens_out,
                }
            if cost > 0:
                kwargs["cost_details"] = {"total": cost}
        if self.include_content:
            kwargs["input"] = span.get("input")
            kwargs["output"] = span.get("output")
        observation = root.start_observation(**kwargs)
        observation.end()

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.flush()
            finally:
                self._client = None
