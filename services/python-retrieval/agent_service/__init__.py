# -*- coding: utf-8 -*-
"""agent_service —— Function Calling 智能体（ReAct + 白名单工具）的 HTTP 服务化封装。

对外暴露 `POST /api/v1/agent/chat`（Result 包络）与 `GET /api/health`。
导入本包不触发模型装配（懒加载），入口见 `python -m agent_service`。
"""

__all__ = ["create_app"]


def __getattr__(name):
    if name == "create_app":
        from .app import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")