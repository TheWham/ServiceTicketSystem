# -*- coding: utf-8 -*-
"""链路追踪内核已抽为共享模块（agent_service 与本演示共用同一实现），此处仅转发。"""
from rag_pipeline.observability.tracer import (  # noqa: F401
    KIND_EVALUATOR, KIND_GATE, KIND_GENERATION, KIND_PARALLEL, KIND_ROUTER, KIND_SPAN,
    STATUS_FAILED, STATUS_INTERCEPTED, STATUS_SKIPPED, STATUS_SUCCESS,
    TOKENS_ESTIMATED, TOKENS_NONE, TOKENS_REPORTED,
    SpanRecord, SpanScope, Tracer, brief, print_trace_dashboard)
