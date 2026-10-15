# -*- coding: utf-8 -*-
"""rag_service —— rag_pipeline 检索内核的 HTTP 服务化封装。

对外暴露 Java rag-service 期望的 `POST /api/v1/rag/retrievals`（Result 包络）
与 `GET /api/health`。导入本包不触发重装配（懒加载），入口见 `python -m rag_service`。
"""

__all__ = ["create_app", "ServiceAssembly"]


def __getattr__(name):
    if name == "create_app":
        from .app import create_app
        return create_app
    if name == "ServiceAssembly":
        from .assembly import ServiceAssembly
        return ServiceAssembly
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
