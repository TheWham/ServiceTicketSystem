# -*- coding: utf-8 -*-
"""rag_service —— rag_pipeline 检索内核的 HTTP 服务化封装。

对外暴露三个端点：

- `POST /api/v1/rag/retrievals`：Java rag-service 期望的检索契约（Result 包络）；
- `POST /api/v1/policy/resolve`：版本消歧查询——给定主题与时间点，解析该时刻有效的规约版本。
  **无 Java 消费方**，是 Python 侧自有的能力，见 `rag_pipeline.policy`；
- `GET /api/health`：自检。

导入本包不触发重装配（懒加载），入口见 `python -m rag_service`。
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
