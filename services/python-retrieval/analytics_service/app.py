# -*- coding: utf-8 -*-
"""FastAPI 应用：分析链路的 HTTP 出口。

- `POST /api/v1/analytics/query` → 跑一次分析链路，返回结论 + facts + 完整链路追踪
- `GET  /api/health`             → 自检（模型是否配置、词表版本、闸门阈值），不调模型

统一 Result 包络（`{code,msg,data}`，code=0 成功），与 rag_service / agent_service /
workflow_demo 一致。

**接口只做参数校验，不做任何业务判定** —— 意图路由、聚合、门禁一律留给链路节点，
保证 HTTP 调用与终端跑的是同一条链路、同一份结论。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from rag_service.contract import ResultEnvelope

from . import config as cfg
from . import taxonomy as tx
from .contract import AnalyticsRunRequest
from .engine import AnalyticsWorkflow


def create_app(workflow: AnalyticsWorkflow | None = None) -> FastAPI:
    """构造应用；workflow 可注入（测试用），默认按请求身份动态装配。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.workflow = workflow
        yield

    app = FastAPI(title="analytics-service (cross-ticket aggregate)",
                  version="0.1.0", lifespan=lifespan)
    app.state.workflow = workflow

    def _ok(data: object) -> JSONResponse:
        return JSONResponse(
            content=ResultEnvelope.ok(data).model_dump(by_alias=True, exclude_none=True))

    def _err(code: int, msg: str, status: int = 400) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content=ResultEnvelope.err(code, msg).model_dump(by_alias=True, exclude_none=True))

    @app.exception_handler(RequestValidationError)
    async def _on_validation(request: Request, exc: RequestValidationError):
        return _err(4000, f"请求参数非法：{exc.errors()[:1]}")

    # ---------------------------------------------------------------- API

    @app.post("/api/v1/analytics/query")
    async def query(req: AnalyticsRunRequest):
        """分析链路的 HTTP 入口。"""
        question = (req.question or "").strip()
        if not question:
            return _err(4001, "question 不能为空")
        if not req.role.strip():
            # 身份缺失一律拒绝：跨人聚合不能靠调用方"自报一个角色"就放行
            return _err(4002, "缺少调用方角色（role），无法判定分析权限")
        try:
            wf = app.state.workflow or AnalyticsWorkflow()
            result = wf.run(question, user_id=req.user_id.strip(),
                            role=req.role.strip(), request_id=req.request_id.strip(),
                            upstream_intent=req.upstream_intent.strip())
        except Exception as e:  # noqa: BLE001 —— 兜底，避免 500 丢栈给前端
            return _err(5000, f"分析链路执行异常：{type(e).__name__}: {e}", status=500)
        return _ok(result)

    @app.get("/api/health")
    async def health():
        """自检：不调模型、不取数，只报配置与词表状态。"""
        try:
            tax = tx.load_taxonomy()
            tax_info = {"version": tax.version, "fingerprint": tax.fingerprint,
                        "domainCount": len(tax.domains),
                        "counts": {axis: len(kws) for axis, kws in tax.keywords.items()}}
        except Exception as e:  # noqa: BLE001 —— 词表坏了也要能自检出来
            tax_info = {"error": f"{type(e).__name__}: {e}"}
        # 策略配置（备件系数）同报：它一改，历史的备件建议就不可复现 ——
        # 运维需要能一眼看到当前生效的是哪个版本。
        try:
            from . import aggregate as agg
            pol = agg.load_policy()
            policy_info = {"version": pol.version, "fingerprint": pol.fingerprint,
                           "sparePartRules": len(pol.spare_part_rules)}
        except Exception as e:  # noqa: BLE001
            policy_info = {"error": f"{type(e).__name__}: {e}"}
        return _ok({
            "status": "UP",
            "modelConfigured": cfg.model_configured(),
            "model": cfg.LLM_MODEL if cfg.model_configured() else None,
            # 请求理解是否走模型（意图 + 槽位）。运维要能一眼看出"这台是不是纯规则模式"——
            # 时间口径是模型抽的还是正则解析的，直接决定排查方向。
            "modelRouting": cfg.MODEL_ROUTING_ENABLED,
            "ticketServiceBaseUrl": cfg.TICKET_SERVICE_BASE_URL,
            "taxonomy": tax_info,
            "policy": policy_info,
            "gates": {"minUniverse": cfg.MIN_UNIVERSE, "minDenom": cfg.MIN_DENOM,
                      "minLabelHits": cfg.MIN_LABEL_HITS,
                      "minCoverageWarn": cfg.MIN_COVERAGE_WARN},
            "allowedRoles": sorted(cfg.ALLOWED_ROLES),
        })

    return app


app = create_app()