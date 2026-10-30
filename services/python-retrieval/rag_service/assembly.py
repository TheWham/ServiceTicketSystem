# -*- coding: utf-8 -*-
"""进程级单例装配：配置 / 语料 / 向量库 / 混合检索器 / 查询改写 / wiki→Java 映射 / 检索锁。

复刻 `rag_pipeline/pipelines/evaluation.py` 的装配路径（含 reranker_backend 显式传入，
与黄金集基线同参），并做两处在线化收紧：
- reranker 限流等待预算与重试次数收敛——否则 429 时工作线程会抱着 search_lock
  重试满 90s，Java 客户端早已断开，后续请求全部排队超时；
- 查询改写 1.2s 短超时且不重试，可用 RAG_DISABLE_QUERY_REWRITE=true 整体关闭。

路径一律经 REPO_ROOT 绝对化（configs/pipeline.yaml 里是相对路径），
非仓库根启动（RAG_HOME 注入）也不会找不到向量库。
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline.chunking.corpus import load_corpus_with_deterministic_ids
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.config import REPO_ROOT, build_gate, config_fingerprint, load_config
from rag_pipeline.docstore import build_docstore
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.graph.engine import Neo4jKnowledgeGraph
from rag_pipeline.graph.reasoner import GraphEnhancedReasoner, extract_query_entities
from rag_pipeline.graph.router import AdaptiveQueryRouter, IntentAnalysisResult
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.retrieval.query_rewriter import QueryRewriter

from .contract import HealthResponse, RagRetrievalResponse, RetrievalRequest
from .mapping import build_response

try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    Chroma = None

from rag_pipeline.store import SimpleVectorStore


class LockBusy(RuntimeError):
    """取锁超时：并发检索打满，快速失败（HTTP 503 / code=5031）。"""


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class ServiceAssembly:
    """检索内核的单例装配体：构造即完成全部校验（指纹不符/缺库即 fail-fast）。"""

    def __init__(self) -> None:
        self.cfg = load_config()
        rc = self.cfg.retrieval

        self.wiki_dir = Path(os.environ.get("RAG_WIKI_DIR") or (REPO_ROOT / "artifacts/output/wiki"))
        self.chroma_dir = Path(os.environ.get("RAG_CHROMA_DIR") or (REPO_ROOT / self.cfg.store_persist_dir))

        # ---- 1) 语料（确定性 chunk_id，与黄金集基线同源）----
        self.corpus = load_corpus_with_deterministic_ids(self.wiki_dir, self.cfg)
        self.parent_category: Dict[str, str] = {}
        for chunk in self.corpus:
            pid = chunk.metadata.get("parent_id") or chunk.metadata.get("wiki_id")
            cat = chunk.metadata.get("wiki_category")
            if pid and cat:
                self.parent_category.setdefault(pid, cat)
        # 指纹先算：向量库加载前要用它做 manifest 校验
        self.wiki_fingerprint = compute_wiki_fingerprint(
            sorted(p for p in self.wiki_dir.glob("*.md") if p.name != "_index.md"))
        self.config_fingerprint = config_fingerprint(self.cfg)

        # ---- 2) 向量库（manifest 指纹校验失败即 fail-fast，不做内存重建）----
        self.vector_db = self._load_vector_db()

        # ---- 2.5) 文档存储（MySQL Docstore，管理父块正文）----
        self.docstore = build_docstore(self.cfg)

        # ---- 3) 检索器（与 evaluation.py 同参，reranker_backend 显式传入）----
        self.retriever = IndustrialHybridRetriever(
            vector_db=self.vector_db,
            corpus_docs=self.corpus,
            reranker_model_name=self.cfg.reranker_model,
            default_exclude=rc.default_exclude,
            reranker_backend=self.cfg.reranker_backend,
            docstore=self.docstore,
        )
        # 在线收紧限流预算：实例级覆盖（类属性/实例默认值均可安全遮蔽，离线评测行为不变）
        self.rerank_wait_budget = float(os.environ.get("RAG_RERANK_WAIT_BUDGET", "1.5"))
        self.rerank_max_retries = int(os.environ.get("RAG_RERANK_MAX_RETRIES", "8"))
        self.rerank_request_timeout = float(os.environ.get("RAG_RERANK_REQUEST_TIMEOUT", "2.5"))
        self.retriever.reranker.RATE_LIMIT_WAIT_BUDGET = self.rerank_wait_budget
        self.retriever.reranker.backend_retries = self.rerank_max_retries
        # 单次上游请求读超时必须小于 Java 客户端总预算——否则一次上游挂起（原默认 120s）
        # 会抱着串行锁占住线程池，后续请求全部 5031
        self.retriever.reranker.REQUEST_TIMEOUT_SECONDS = self.rerank_request_timeout

        # ---- 4) 查询改写（1.2s 短超时、不重试；可整体关闭）----
        self.rewrite_disabled = _env_bool("RAG_DISABLE_QUERY_REWRITE", False)
        self.rewrite_timeout = float(os.environ.get("RAG_REWRITE_TIMEOUT", "2.0"))
        self.rewriter: Optional[QueryRewriter] = None
        if rc.query_rewrite and not self.rewrite_disabled:
            cache_dir = os.environ.get("RAG_REWRITE_CACHE_DIR") or str(
                REPO_ROOT / "artifacts/evaluation/.llm_cache/rewrite")
            # 预算倒推：Java 客户端 4.2s = 改写 T + 向量/BM25 ~0.7s + 精排 ≤1.5s（在线收紧后）
            # ⇒ T ≤ 2.0s；实测网关改写延迟 0.8~2.1s（中位 1.7s），取 2.0s 兼顾成功率与预算。
            # max_retries=0 必须显式传：SDK 默认自带重试会让一次改写变成 T×3。
            self.rewriter = QueryRewriter(
                model=rc.rewrite_model, cache_dir=cache_dir,
                timeout=self.rewrite_timeout, retries=1, max_retries=0)

        # ---- 5) wiki→Java 映射（缺失即 DEGRADED，不阻断启动）----
        self.mapping_path = Path(os.environ.get("RAG_MAPPING_PATH")
                                 or (REPO_ROOT / "data/wiki_article_mapping.json"))
        self.mapping: Dict[str, Dict[str, Any]] = {}
        if self.mapping_path.exists():
            try:
                self.mapping = json.loads(self.mapping_path.read_text(encoding="utf-8")) or {}
            except Exception as e:      # noqa: BLE001 —— 映射损坏按 DEGRADED 处理，不阻断检索
                print(f"⚠️ 映射文件解析失败（{self.mapping_path}）：{e}，按未加载处理")

        # ---- 5.5) 自适应意图与实体分析器（单维走双召回，多维走 GraphRAG）----
        router_cache_dir = os.environ.get("RAG_ROUTER_CACHE_DIR") or str(
            REPO_ROOT / "artifacts/evaluation/.llm_cache/router")
        self.router = AdaptiveQueryRouter(
            cache_dir=router_cache_dir,
            timeout=float(os.environ.get("RAG_ROUTER_TIMEOUT", "3.0")),
        )

        # ---- 5.6) Neo4j 知识图谱与双轨推理器（可选依赖，故障优雅降级）----
        self.kg: Optional[Neo4jKnowledgeGraph] = None
        self.reasoner: Optional[GraphEnhancedReasoner] = None
        try:
            self.kg = Neo4jKnowledgeGraph()
            node_cnt = self.kg.count_nodes()
            if node_cnt == 0:
                print("⚠️ Neo4j 节点数为 0，自动全量同步三元组构建知识图谱...")
                try:
                    from tools.sync_triples_to_neo4j import main as sync_neo4j_main
                    sync_neo4j_main()
                    node_cnt = self.kg.count_nodes()
                except Exception as sync_err:
                    print(f"⚠️ 自动同步知识图谱失败: {sync_err}")
            self.reasoner = GraphEnhancedReasoner(kg=self.kg, docstore=self.docstore)
            print(f"✅ Neo4j 知识图谱挂载就绪（节点数={node_cnt}）")
        except Exception as e:
            print(f"⚠️ Neo4j 图数据库未就绪或连接失败: {e}，图谱推理能力暂不可用")

        # ---- 6) 检索锁（可配置安全开关）----
        self.serialize_search = _env_bool("RAG_SERIALIZE_SEARCH", True)
        self.lock_wait_seconds = float(os.environ.get("RAG_LOCK_WAIT_SECONDS", "1.0"))
        self._lock = threading.Lock()
        self.rerank_degraded_count = 0
        # 版本消歧解析器（懒构造，与检索器共用同一份语料与向量库）
        self._policy_resolver: Optional[Any] = None

    # ------------------------------------------------------------------ 装配细节

    def _load_vector_db(self) -> Any:
        manifest_file = self.chroma_dir / "manifest.json"
        if not self.chroma_dir.exists():
            raise RuntimeError(f"❌ 向量库目录不存在：{self.chroma_dir}（请先运行 indexing 流水线）")
        if not manifest_file.exists():
            raise RuntimeError(f"❌ 缺少 manifest：{manifest_file}（旧版向量库，拒绝启动）")

        saved = json.loads(manifest_file.read_text(encoding="utf-8"))
        if saved.get("wiki_fingerprint") != self.wiki_fingerprint:
            raise RuntimeError("❌ 向量库与当前 Wiki 卡片不一致（wiki_fingerprint 漂移），请重建索引")
        if saved.get("config_fingerprint") and saved["config_fingerprint"] != self.config_fingerprint:
            raise RuntimeError("❌ 向量库与当前切片配置不一致（config_fingerprint 漂移），请重建索引")

        embed_provider = KspEmbeddingProvider(cache_dir=str(REPO_ROOT / self.cfg.embedding_cache_dir))
        if Chroma is not None:
            return Chroma(persist_directory=str(self.chroma_dir),
                          embedding_function=embed_provider,
                          collection_name=self.cfg.store_collection)
        # 环境未安装 chromadb 时直读 chroma.sqlite3 中的真实向量
        return SimpleVectorStore.from_chroma_sqlite(str(self.chroma_dir), embed_provider)

    # ------------------------------------------------------------------ 检索 

    def search(self, req: RetrievalRequest) -> RagRetrievalResponse:
        """【链路二 · 在线主链路入口】Assembly.search(req)
        
        输入：RetrievalRequest 对象（包含 question, category_id, top_k 等）。
        动作：
          1. 步骤 1 (意图分流)：router.analyze(req.question)，单维事实跳过图谱（0ms开销），复合故障触发图谱；
          2. 步骤 2 (实体去噪)：extract_query_entities 提取故障关键实体并执行泛化去噪；
          3. 步骤 3 (双轨检索)：reasoner.retrieve_multihop_context 执行 Neo4j 2-Hop 剪枝遍历与 MySQL Docstore 全文回溯；
          4. 步骤 4 (主路混合)：_run_search 执行向量库 + BM25 双路召回与 Cross-Encoder Rerank 精排；
          5. 步骤 5 (契约装配)：build_response 将图谱推导因果链前置注入到 Top-1 切片正文并组装契约响应。
        返回：RagRetrievalResponse 工业级对外标准检索响应体。
        """
        # 步骤 1: 自适应意图判别与实体抽取（单维走双路召回，多维走 GraphRAG）
        intent_res = self.router.analyze(req.question)
        reasoning_res = None

        # 步骤 2 & 3: 仅在识别为复合故障且图谱组件就绪时，执行图谱多跳因果推导
        if intent_res.needs_graph and self.kg and self.reasoner:
            try:
                # 动态获取图谱实体全集，杜绝静态死词表
                candidate_nodes = self.kg.get_all_node_names()
                extracted_terms = " ".join(intent_res.extracted_entities)
                combined_query = f"{req.question} {extracted_terms}".strip()
                # 步骤 2: 提取种子实体并泛化去噪
                seed_entities = extract_query_entities(combined_query, candidate_nodes=candidate_nodes)
                if seed_entities:
                    # 步骤 3: 双轨检索（轨A图谱BFS事实抽取 + 轨B MySQL Docstore 全文回溯）
                    reasoning_res = self.reasoner.retrieve_multihop_context(
                        req.question, seed_entities=seed_entities, max_hops=2
                    )
            except Exception as e:
                print(f"⚠️ 自适应图谱推导执行异常（安全跳过）: {e}")

        # 步骤 4: 竞争锁保护下的主路双路混合检索（向量 + BM25 + Cross-Encoder 重排）
        if self.serialize_search:
            if not self._lock.acquire(timeout=self.lock_wait_seconds):
                raise LockBusy(f"检索锁等待超过 {self.lock_wait_seconds}s")
            try:
                res = self._run_search(req)
            finally:
                self._lock.release()
        else:
            res = self._run_search(req)

        if res.get("rerank_remote") is False:
            # 网关限流 → 启发式降级：内核拒答门会被跳过，服务层阈值判定仍生效（见 mapping.build_response）
            self.rerank_degraded_count += 1
            print(f"⚠️ rerank 降级为启发式打分（累计 {self.rerank_degraded_count} 次）："
                  f"max={res.get('max_rerank_score')} 「{req.question[:40]}」")

        # 步骤 5: 组装对外标准契约响应（并在 Top-1 片段前置注入图谱因果推导链）
        return build_response(res, wiki_mapping=self.mapping,
                              request_category_id=req.category_id,
                              reject_threshold=self.cfg.retrieval.reject_threshold,
                              docstore=self.docstore,
                              reasoning_res=reasoning_res)

    def _run_search(self, req: RetrievalRequest) -> Dict[str, Any]:
        rc = self.cfg.retrieval
        rewrite = self.rewriter.rewrite(req.question) if self.rewriter else None
        return self.retriever.hybrid_rerank_search(
            query=req.question,
            final_top_k=req.top_k,
            rrf_k=rc.rrf_k,
            rough_top_k=rc.rough_top_k,
            fuse_k=rc.fuse_k,
            rrf_weight=rc.rrf_weight,
            rerank_weight=rc.rerank_weight,
            metadata_filter=self._metadata_filter(req.category_id),
            reject_threshold=rc.reject_threshold,
            heuristic_reject_threshold=rc.heuristic_reject_threshold,
            rerank_granularity=rc.rerank_granularity,
            rewrite_query=rewrite,
            gate=build_gate(rc),
        )

    def _metadata_filter(self, category_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Java 的 categoryId 是类目编码（如 C_NET），wiki_category 是中文名。

        仅在映射表能反查出**唯一**中文类目时才做硬过滤；否则不传 filter（编码塞进
        元数据过滤会滤空）。多类目歧义同样放弃过滤，交给调用方后续处理。
        """
        if not category_id or not self.mapping:
            return None
        wiki_ids = [wid for wid, entry in self.mapping.items()
                    if (entry or {}).get("categoryId") == category_id]
        chinese = {self.parent_category.get(wid) for wid in wiki_ids}
        chinese.discard(None)
        if len(chinese) == 1:
            return {"wiki_category": next(iter(chinese))}
        return None

    # ------------------------------------------------------------------ 版本消歧

    def resolve_policy(self, query: str, at: Optional[str] = None, top_k: int = 8):
        """版本消歧查询：给定主题与时间点，解析该时刻有效的规约版本。

        见 `rag_pipeline.policy`。与 `search()` 共用同一把检索锁——两者都会跑一次完整
        检索，不串行会让 rerank 的限流预算互相挤占。
        """
        from rag_pipeline.policy import PolicyResolver

        if self._policy_resolver is None:
            self._policy_resolver = PolicyResolver(self.retriever)

        if self.serialize_search:
            if not self._lock.acquire(timeout=self.lock_wait_seconds):
                raise LockBusy(f"检索锁等待超过 {self.lock_wait_seconds}s")
            try:
                return self._policy_resolver.resolve(query, at=at, top_k=top_k)
            finally:
                self._lock.release()
        return self._policy_resolver.resolve(query, at=at, top_k=top_k)

    # ------------------------------------------------------------------ 自检

    def health_info(self) -> HealthResponse:
        mapping_loaded = bool(self.mapping)
        return HealthResponse(
            status="UP" if mapping_loaded else "DEGRADED",
            chunk_count=len(self.corpus),
            wiki_fingerprint=self.wiki_fingerprint,
            config_fingerprint=self.config_fingerprint,
            mapping_loaded=mapping_loaded,
            mapping_entries=len(self.mapping),
            query_rewrite=self.rewriter is not None,
            rewrite_timeout=self.rewrite_timeout,
            serialize_search=self.serialize_search,
            lock_wait_seconds=self.lock_wait_seconds,
            rerank_wait_budget=self.rerank_wait_budget,
            rerank_max_retries=self.rerank_max_retries,
            rerank_request_timeout=self.rerank_request_timeout,
            rerank_available=bool(getattr(self.retriever.reranker, "available", False)),
            rerank_provider=getattr(self.retriever.reranker, "provider", "unknown"),
            rerank_degraded_count=self.rerank_degraded_count,
        )
