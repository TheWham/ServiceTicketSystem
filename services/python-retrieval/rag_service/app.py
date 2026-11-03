# -*- coding: utf-8 -*-
"""FastAPI 应用：rag_pipeline 检索内核的 HTTP 出口。

- `POST /api/v1/rag/retrievals`：**同步 def**（Starlette 线程池执行，不阻塞事件循环），
  内部经 search_lock 串行（可配置）；取锁超时 → HTTP 503 + code=5031。
- `POST /api/v1/policy/resolve`：**同步 def**，同上走线程池与 search_lock。
  版本消歧查询（见 `rag_pipeline.policy`）：给定主题与时间点，解析该时刻有效的规约版本。
  注意 `data.status` 有四态，其中 `UNDATED` / `NO_MATCH` 是**结论不是失败**，仍是 HTTP 200。
- `GET /api/health`：**async def**，不抢检索锁——检索打满时仍 0ms 级响应，
  并回显在线预算（rerankWaitBudget/rerankMaxRetries）便于确认收紧已生效。
- 统一 Result 包络（{code,msg,data}，code=0 成功），异常映射：锁定 5031 / 参数 4000 / 兜底 5000。
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .assembly import LockBusy, ServiceAssembly
from .contract import PolicyResolveRequest, ResultEnvelope, RetrievalRequest


def create_app(assembly: ServiceAssembly = None) -> FastAPI:
    """构造应用；assembly 可注入（测试用），默认在 lifespan 中装配。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.assembly = assembly or ServiceAssembly()
        yield

    app = FastAPI(title="rag-service (python retrieval kernel)", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if assembly is not None:
        app.state.assembly = assembly

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

    @app.post("/api/v1/policy/resolve")
    def resolve_policy(req: PolicyResolveRequest):   # 同步 def：同 retrievals，走线程池
        """版本消歧：给定主题与时间点，解析该时刻有效的规约版本（含溯源角标）。

        data.status ∈ RESOLVED / NO_EFFECTIVE_VERSION / UNDATED / NO_MATCH，
        四态不互相冒充——尤其 UNDATED 表示「相关卡片没有生效日期，无法判定」，不是失败。
        """
        asm: ServiceAssembly = app.state.assembly
        return ResultEnvelope.ok(asm.resolve_policy(req.query, at=req.at, top_k=req.top_k).to_dict()) \
            .model_dump(by_alias=True, exclude_none=True)

    @app.get("/api/neo4j/graph_data")
    def get_neo4j_graph_data(scene: str = "vpn", entities: str = ""):
        """从 Neo4j 动态读取特定场景或指定实体列表的子图拓扑数据用于前端可视化。"""
        asm: ServiceAssembly = app.state.assembly
        kg = asm.kg
        if not kg:
            return JSONResponse(content={"code": 0, "data": {"nodes": [], "edges": []}})

        try:
            entity_list = [e.strip() for e in entities.split(",") if e.strip()] if entities else []
            params = {}
            if entity_list:
                cypher = """
                MATCH (e)
                WHERE e.name IN $entity_list OR any(ent IN $entity_list WHERE e.name CONTAINS ent)
                WITH collect(e) AS seeds
                UNWIND seeds AS s
                MATCH path = (s)-[r*1..2]-(m)
                UNWIND relationships(path) AS rel
                RETURN DISTINCT startNode(rel).name AS source, type(rel) AS rel, endNode(rel).name AS target,
                       coalesce(startNode(rel).is_deprecated, false) AS src_dep,
                       coalesce(endNode(rel).is_deprecated, false) AS tgt_dep,
                       coalesce(rel.quote, '') AS quote
                LIMIT 60
                """
                params["entity_list"] = entity_list
            elif scene == "vpn":
                cypher = """
                MATCH path = (e {name: 'VPN错误691'})-[r*1..2]-(m)
                UNWIND relationships(path) AS rel
                RETURN DISTINCT startNode(rel).name AS source, type(rel) AS rel, endNode(rel).name AS target,
                       coalesce(startNode(rel).is_deprecated, false) AS src_dep,
                       coalesce(endNode(rel).is_deprecated, false) AS tgt_dep,
                       coalesce(rel.quote, '') AS quote
                LIMIT 50
                """
            elif scene == "replaces":
                cypher = """
                MATCH (e)-[r:废止并替代|REPLACES]->(m)
                RETURN e.name AS source, type(r) AS rel, m.name AS target,
                       coalesce(e.is_deprecated, false) AS src_dep,
                       coalesce(m.is_deprecated, false) AS tgt_dep,
                       coalesce(r.quote, '') AS quote
                LIMIT 50
                """
            elif scene == "cmdb":
                cypher = """
                MATCH path = (e {name: '财务报销系统'})-[*1..2]-(m)
                UNWIND relationships(path) AS rel
                RETURN DISTINCT startNode(rel).name AS source, type(rel) AS rel, endNode(rel).name AS target,
                       coalesce(startNode(rel).is_deprecated, false) AS src_dep,
                       coalesce(endNode(rel).is_deprecated, false) AS tgt_dep,
                       coalesce(rel.quote, '') AS quote
                LIMIT 50
                """
            else:
                cypher = """
                MATCH (n)-[r]->(m)
                RETURN n.name AS source, type(r) AS rel, m.name AS target,
                       coalesce(n.is_deprecated, false) AS src_dep,
                       coalesce(m.is_deprecated, false) AS tgt_dep,
                       coalesce(r.quote, '') AS quote
                LIMIT 60
                """

            nodes_map = {}
            edges = []

            with kg.driver.session() as s:
                records = list(s.run(cypher, **params) if params else s.run(cypher))
                for rec in records:
                    src = rec["source"]
                    tgt = rec["target"]
                    rel = rec["rel"]
                    src_dep = rec["src_dep"]
                    tgt_dep = rec["tgt_dep"]
                    quote = rec["quote"]

                    if src not in nodes_map:
                        nodes_map[src] = {"id": src, "label": src, "is_deprecated": src_dep}
                    if tgt not in nodes_map:
                        nodes_map[tgt] = {"id": tgt, "label": tgt, "is_deprecated": tgt_dep}

                    edges.append({
                        "from": src,
                        "to": tgt,
                        "label": rel,
                        "title": quote or rel,
                    })

            return JSONResponse(content={
                "code": 0,
                "data": {
                    "nodes": list(nodes_map.values()),
                    "edges": edges,
                }
            })
        except Exception as e:
            return JSONResponse(status_code=500, content={"code": 1, "error": str(e)})

    # ---- 挂载 LangGraph 知识库沉淀流程编排路由 ----
    try:
        import sys
        from pathlib import Path
        py_retrieval_dir = str(Path(__file__).resolve().parents[1])
        if py_retrieval_dir not in sys.path:
            sys.path.insert(0, py_retrieval_dir)
        from knowledge_flow.router import router as knowledge_flow_router
        app.include_router(knowledge_flow_router)
    except Exception as e:
        import logging
        logging.getLogger("rag_service").warning("知识库流程编排路由挂载跳过: %s", e)

    return app
