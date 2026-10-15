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
from rag_pipeline.embedding import KspEmbeddingProvider
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

        # ---- 3) 检索器（与 evaluation.py 同参，reranker_backend 显式传入）----
        self.retriever = IndustrialHybridRetriever(
            vector_db=self.vector_db,
            corpus_docs=self.corpus,
            reranker_model_name=self.cfg.reranker_model,
            default_exclude=rc.default_exclude,
            reranker_backend=self.cfg.reranker_backend,
        )
        # 在线收紧限流预算：实例级覆盖（类属性/实例默认值均可安全遮蔽，离线评测行为不变）
        self.rerank_wait_budget = float(os.environ.get("RAG_RERANK_WAIT_BUDGET", "1.5"))
        self.rerank_max_retries = int(os.environ.get("RAG_RERANK_MAX_RETRIES", "8"))
        self.retriever.reranker.RATE_LIMIT_WAIT_BUDGET = self.rerank_wait_budget
        self.retriever.reranker.backend_retries = self.rerank_max_retries

        # ---- 4) 查询改写（1.2s 短超时、不重试；可整体关闭）----
        self.rewrite_disabled = _env_bool("RAG_DISABLE_QUERY_REWRITE", False)
        self.rewriter: Optional[QueryRewriter] = None
        if rc.query_rewrite and not self.rewrite_disabled:
            cache_dir = os.environ.get("RAG_REWRITE_CACHE_DIR") or str(
                REPO_ROOT / "artifacts/evaluation/.llm_cache/rewrite")
            self.rewriter = QueryRewriter(
                model=rc.rewrite_model, cache_dir=cache_dir, timeout=1.2, retries=1)

        # ---- 5) wiki→Java 映射（缺失即 DEGRADED，不阻断启动）----
        self.mapping_path = Path(os.environ.get("RAG_MAPPING_PATH")
                                 or (REPO_ROOT / "data/wiki_article_mapping.json"))
        self.mapping: Dict[str, Dict[str, Any]] = {}
        if self.mapping_path.exists():
            try:
                self.mapping = json.loads(self.mapping_path.read_text(encoding="utf-8")) or {}
            except Exception as e:      # noqa: BLE001 —— 映射损坏按 DEGRADED 处理，不阻断检索
                print(f"⚠️ 映射文件解析失败（{self.mapping_path}）：{e}，按未加载处理")

        # ---- 6) 检索锁（可配置安全开关）----
        self.serialize_search = _env_bool("RAG_SERIALIZE_SEARCH", True)
        self.lock_wait_seconds = float(os.environ.get("RAG_LOCK_WAIT_SECONDS", "1.0"))
        self._lock = threading.Lock()
        self.rerank_degraded_count = 0

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
        """串行（可关）执行一次检索并装配契约响应。"""
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

        return build_response(res, wiki_mapping=self.mapping,
                              request_category_id=req.category_id,
                              reject_threshold=self.cfg.retrieval.reject_threshold)

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
            serialize_search=self.serialize_search,
            lock_wait_seconds=self.lock_wait_seconds,
            rerank_wait_budget=self.rerank_wait_budget,
            rerank_max_retries=self.rerank_max_retries,
            rerank_available=bool(getattr(self.retriever.reranker, "available", False)),
            rerank_provider=getattr(self.retriever.reranker, "provider", "unknown"),
            rerank_degraded_count=self.rerank_degraded_count,
        )
