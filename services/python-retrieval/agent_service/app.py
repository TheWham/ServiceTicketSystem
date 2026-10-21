# -*- coding: utf-8 -*-
"""FastAPI 应用：Function Calling 智能体（ReAct + 白名单工具）的 HTTP 出口。

- `POST /api/v1/agent/chat`：**同步 def**（Starlette 线程池执行，不阻塞事件循环）。
  主体由 `X-User-Id` / `X-User-Role` 头透传（归属安全，不接受请求体指定操作者）。
- `GET /api/health`：自检（模型/工具是否已配置），不调用模型。
- 统一 Result 包络（`{code,msg,data}`，code=0 成功）；模型不可用 → 503 code=5032。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from rag_service.contract import ResultEnvelope

from . import config as acfg
from .agent import AgentRunner
from .contract import AgentChatRequest
from .model_client import ModelError


def create_app(runner: AgentRunner = None) -> FastAPI:
    """构造应用；runner 可注入（测试用），默认首个请求时懒加载。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runner = runner
        yield

    app = FastAPI(title="agent-service (function calling)", version="0.1.0", lifespan=lifespan)
    app.state.runner = runner        # 可注入；None 表示首个请求懒加载（模型未配置也不崩）

    def _envelope(code: int, msg: str) -> dict:
        return ResultEnvelope.err(code, msg).model_dump(by_alias=True, exclude_none=True)

    @app.exception_handler(RequestValidationError)
    async def _on_validation(request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content=_envelope(4000, f"请求参数非法：{exc.errors()[:1]}"))

    @app.exception_handler(ModelError)
    async def _on_model_unavailable(request, exc: ModelError):
        return JSONResponse(status_code=503, content=_envelope(5032, f"生成不可用：{exc}"))

    @app.exception_handler(Exception)
    async def _on_error(request, exc: Exception):
        return JSONResponse(status_code=500, content=_envelope(5000, f"{type(exc).__name__}: {exc}"))

    @app.get("/api/health")
    async def health():
        return {"status": "UP", "model_configured": acfg.model_configured(), "model": acfg.LLM_MODEL,
                "max_steps": acfg.MAX_STEPS,
                "ticket_service_configured": bool(acfg.TICKET_SERVICE_BASE_URL),
                "knowledge_search_configured": bool(acfg.KNOWLEDGE_SEARCH_BASE_URL)}

    @app.post("/api/v1/agent/chat")
    def chat(req: AgentChatRequest,
             x_user_id: str = Header(default="", alias="X-User-Id"),
             x_user_role: str = Header(default="", alias="X-User-Role")):
        runner_ = app.state.runner
        if runner_ is None:                       # 懒加载：模型未配置时启动不崩，请求时才报 503
            runner_ = AgentRunner()
            app.state.runner = runner_
        response = runner_.run(req, x_user_id, x_user_role)
        return ResultEnvelope.ok(response.model_dump(by_alias=True, exclude_none=True)) \
            .model_dump(by_alias=True, exclude_none=True)

    return app