# -*- coding: utf-8 -*-
"""FastAPI 应用：rag_pipeline 检索内核的 HTTP 出口。

- `POST /api/v1/rag/retrievals`：**同步 def**（Starlette 线程池执行，不阻塞事件循环），
  内部经 search_lock 串行（可配置）；取锁超时 → HTTP 503 + code=5031。
- `GET /api/health`：**async def**，不抢检索锁——检索打满时仍 0ms 级响应，
  并回显在线预算（rerankWaitBudget/rerankMaxRetries）便于确认收紧已生效。
- 统一 Result 包络（{code,msg,data}，code=0 成功），异常映射：锁定 5031 / 参数 4000 / 兜底 5000。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .assembly import LockBusy, ServiceAssembly
from .contract import ResultEnvelope, RetrievalRequest


def create_app(assembly: ServiceAssembly = None) -> FastAPI:
    """构造应用；assembly 可注入（测试用），默认在 lifespan 中装配。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.assembly = assembly or ServiceAssembly()
        yield

    app = FastAPI(title="rag-service (python retrieval kernel)", version="0.1.0", lifespan=lifespan)

    def _envelope(code: int, msg: str) -> dict:
        return ResultEnvelope.err(code, msg).model_dump(by_alias=True, exclude_none=True)

    @app.exception_handler(LockBusy)
    async def _on_lock_busy(request, exc: LockBusy):
        return JSONResponse(status_code=503, content=_envelope(5031, f"检索繁忙，请稍后重试：{exc}"))

    @app.exception_handler(RequestValidationError)
    async def _on_validation(request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content=_envelope(4000, f"请求参数非法：{exc.errors()[:1]}"))

    @app.exception_handler(Exception)
    async def _on_error(request, exc: Exception):
        return JSONResponse(status_code=500, content=_envelope(5000, f"{type(exc).__name__}: {exc}"))

    @app.get("/api/health")
    async def health():
        asm: ServiceAssembly = app.state.assembly
        return asm.health_info().model_dump(by_alias=True, exclude_none=True)

    @app.post("/api/v1/rag/retrievals")
    def retrievals(req: RetrievalRequest):    # 同步 def：Starlette 自动派发到线程池
        asm: ServiceAssembly = app.state.assembly
        resp = asm.search(req)
        return ResultEnvelope.ok(resp.model_dump(by_alias=True, exclude_none=True)) \
            .model_dump(by_alias=True, exclude_none=True)

    return app
