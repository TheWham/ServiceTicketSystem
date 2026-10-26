# -*- coding: utf-8 -*-
"""FastAPI 应用：确定性工作流的 HTTP 出口 + 可视化单页。

- `GET  /`                     → 演示页（单文件，无构建、无外链）
- `GET  /api/v1/workflow/cases`→ 演示用例清单
- `POST /api/v1/workflow/run`  → 跑一次工作流，返回结论 + 完整链路追踪
- `GET  /api/health`           → 自检（是否配了模型、种子库在哪），不调模型

统一 Result 包络（`{code,msg,data}`，code=0 成功），与 rag_service / agent_service 一致。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from rag_service.contract import ResultEnvelope

from . import config as cfg
from .cases import get_case
from .contract import WorkflowRunRequest
from .engine import DeterministicWorkflow, demo_cases

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(workflow: DeterministicWorkflow | None = None) -> FastAPI:
    """构造应用；workflow 可注入（测试用），默认为进程级单例。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.workflow = workflow
        yield

    app = FastAPI(title="workflow-demo (deterministic workflow + tracing)",
                  version="0.1.0", lifespan=lifespan)
    app.state.workflow = workflow

    def _ok(data: object) -> JSONResponse:
        return JSONResponse(content=ResultEnvelope.ok(data).model_dump(by_alias=True, exclude_none=True))

    def _err(code: int, msg: str, status: int = 400) -> JSONResponse:
        return JSONResponse(status_code=status,
                            content=ResultEnvelope.err(code, msg).model_dump(by_alias=True, exclude_none=True))

    def _wf() -> DeterministicWorkflow:
        if app.state.workflow is None:      # 首个请求时装配（种子库按需建）
            app.state.workflow = DeterministicWorkflow()
        return app.state.workflow

    @app.exception_handler(RequestValidationError)
    async def _on_validation(request: Request, exc: RequestValidationError):
        return _err(4000, f"请求参数非法：{exc.errors()[:1]}")

    # ---------------------------------------------------------------- 演示页
    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    # ---------------------------------------------------------------- API
    @app.get("/api/v1/workflow/cases")
    async def cases():
        return _ok({"cases": demo_cases()})

    @app.post("/api/v1/workflow/run")
    async def run(req: WorkflowRunRequest):
        """链路的 HTTP 入口。这里只做参数校验，**不做任何业务判定** ——
        路由、裁决、门禁一律留给工作流节点，保证网页端和终端跑的是同一条链路。
        """
        wf = _wf()
        question = (req.question or "").strip()
        case_id = (req.case_id or "").strip()

        # caseId 只是 question 的快捷方式：查表取出问题文本，之后流程完全一致。
        if not question and not case_id:
            return _err(4001, "question 与 caseId 至少提供一个")
        if case_id and not question:
            case = get_case(case_id)
            if case is None:
                return _err(4002, f"未知用例：{case_id}")
            question = case.question
        if len(question) > cfg.QUESTION_MAX_CHARS:
            return _err(4003, f"question 超长（上限 {cfg.QUESTION_MAX_CHARS} 字）")

        # 进入链路：返回的 result 里既有结论，也有完整的 trace ——
        # 网页端的甘特图与节点明细就是拿 result["trace"] 渲染的，无需再查别的接口。
        user_id = (req.user_id or "").strip() or "U_EMP01"
        try:
            result = wf.run(question, user_id=user_id, case_id=case_id)
        except Exception as e:  # noqa: BLE001 —— 兜底，避免 500 丢栈给前端
            return _err(5000, f"工作流执行异常：{type(e).__name__}: {e}", status=500)

        if case_id:
            case = get_case(case_id)
            if case is not None:
                result["expected"] = case.expect
                result["matched"] = result["verdict"] == case.expect
        return _ok(result)

    @app.get("/api/health")
    async def health():
        return _ok({
            "status": "UP",
            "modelConfigured": cfg.model_configured(),
            "model": cfg.LLM_MODEL if cfg.model_configured() else None,
            "dbPath": str(cfg.DB_PATH),
            "caseCount": len(demo_cases()),
            "duplicateWindowHours": cfg.DUPLICATE_WINDOW_HOURS,
            "priceInputPerM": cfg.PRICE_INPUT_PER_M,
            "priceOutputPerM": cfg.PRICE_OUTPUT_PER_M,
        })

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app


app = create_app()