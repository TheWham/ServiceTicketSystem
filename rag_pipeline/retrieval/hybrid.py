"""工业级双路混合检索 + RRF 融合 + 按秩加权精排重排器。"""

import time
from typing import List, Dict, Any, Tuple, Optional

from langchain_core.documents import Document

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

from .tokenizer import ChineseTokenizer, PurePythonBM25
from .reranker import KspReranker


class IndustrialHybridRetriever:
    """
    工业级混合检索与重排核心中枢：
    - 结构化语料库 BM25 倒排索引
    - Chroma 向量数据库语义检索
    - RRF (Reciprocal Rank Fusion, k=60) 倒数排名融合
    - KspReranker (qwen3-reranker-8b 交叉注意力) 精排
    - 按秩加权融合兜底（rerank 名次 + RRF 名次，免疫远程分数漂移）
    - 支持全生命周期 Metadata Pre-filtering 硬过滤
    """

    def __init__(
        self,
        vector_db: Any,
        corpus_docs: List[Document],
        reranker_model_name: str = "qwen3-reranker-8b",
        default_exclude: Optional[Dict[str, List[str]]] = None,
        reranker_backend: str = "dashscope"
    ):
        self.vector_db = vector_db
        self.corpus_docs = corpus_docs
        # 默认排除清单：如 {"wiki_status": ["已废止"]}。
        # 把 adversarial_benchmark 验证过的"元数据物理屏蔽废止卡"结论固化进主链路；
        # 注意保持可选——对抗压测脚本需要"无过滤"对照组，应显式不传。
        self.default_exclude = default_exclude or {}

        print("🔍 [1/3] 正在对高纯度结构化语料进行分词并构建 BM25 倒排索引...")
        self.tokenized_corpus = [
            ChineseTokenizer.tokenize(doc.page_content) for doc in corpus_docs
        ]

        if BM25Okapi is not None:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = PurePythonBM25(self.tokenized_corpus)

        print(f"⚡ [2/3] 正在初始化 Cross-Encoder 交叉重排模型...")
        self.reranker = KspReranker(model_name=reranker_model_name, backend=reranker_backend)
        print("✅ [3/3] 双路混合检索与重排引擎装配就绪！\n")

    def _is_excluded(self, metadata: Dict[str, Any]) -> bool:
        """默认排除清单判定：命中任一 (字段, 坏值) 即物理屏蔽该切片。"""
        return any(metadata.get(k) in bad for k, bad in self.default_exclude.items())

    def bm25_search(
        self,
        query: str,
        top_k: int = 15,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, int, float]]:
        """BM25 关键词精确检索通道，返回 [(Doc, Rank, BM25_Score)]。

        字面召回：对"工单号/错误码/端口/命令"等专有编号极强（IDF 高），
        恰好补上 Dense 向量检索把这些数字语义稀释掉的盲区。
        """
        tokenized_query = ChineseTokenizer.tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        rank = 1
        for idx in sorted_indices:
            doc = self.corpus_docs[idx]
            # 默认排除（如已废止卡）优先于业务过滤
            if self._is_excluded(doc.metadata):
                continue
            # 校验元数据前置过滤
            if metadata_filter:
                match = all(doc.metadata.get(k) == v for k, v in metadata_filter.items())
                if not match:
                    continue
            results.append((doc, rank, float(scores[idx])))
            rank += 1
            if len(results) >= top_k:
                break
        return results

    def dense_search(
        self,
        query: str,
        top_k: int = 15,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, int, float]]:
        """Dense 语义向量检索通道，返回 [(Doc, Rank, Cosine_Similarity)]。

        语义召回：擅长意图匹配（"打不开网页"≈"无法访问网站"），
        与 BM25 字面召回互补，共同构成双路召回。
        """
        if self.vector_db is None:
            return []

        # Chroma 的 where 只支持等值/范围，"排除"语义在 Python 侧后置过滤；
        # 多取 3 倍再筛，避免排除后 Top-K 不足
        fetch_k = top_k * 3 if self.default_exclude else top_k
        docs_with_scores = self.vector_db.similarity_search_with_relevance_scores(
            query, k=fetch_k, filter=metadata_filter
        )
        if self.default_exclude:
            docs_with_scores = [
                (d, s) for d, s in docs_with_scores if not self._is_excluded(d.metadata)
            ][:top_k]
        results = []
        for rank, (doc, score) in enumerate(docs_with_scores, 1):
            results.append((doc, rank, float(score)))
        return results

    def rrf_fusion(
        self,
        bm25_results: List[Tuple[Document, int, float]],
        dense_results: List[Tuple[Document, int, float]],
        rrf_k: int = 60,
        candidate_limit: int = 15,
        extra_results: Optional[List[List[Tuple[Document, int, float]]]] = None
    ) -> List[Tuple[Document, float]]:
        """
        RRF 倒数排名融合算法：只看名次不看异构绝对分。
        extra_results：额外通道（如改写查询的 BM25/Dense 结果），与前两路同权累加。

        公式：RRF_Score(d) = Σ_channels 1/(k + rank_c(d))
        为什么用名次而非绝对分：BM25 分(0~30+)与余弦分(0~1)量纲完全不同，
        直接相加会被大数值淹没；名次天然归一，零调参即可无损合并两路。
        以 page_content 作为去重键：同一切片若两路都召回，分数累加、排名更前。
        """
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        # 累加 BM25 通道贡献
        for doc, rank, _ in bm25_results:
            key = doc.page_content
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        # 累加 Dense 向量通道贡献（及改写查询等额外通道）
        for channel in [dense_results] + list(extra_results or []):
            for doc, rank, _ in channel:
                key = doc.page_content
                doc_map[key] = doc
                rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:candidate_limit]
        return [(doc_map[key], score) for key, score in sorted_candidates]

    @staticmethod
    def _ranks_of(scores: List[float]) -> List[int]:
        """把分数列表转成名次（1 = 最高），并列（分数相同）取相同名次。

        为什么需要名次化：远程 Reranker 的绝对分会漂移但排序基本稳定，
        取名次后融合对分数漂移免疫（详见讲义第六篇）。
        """
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        ranks = [0] * len(scores)
        for pos, idx in enumerate(order):
            if pos > 0 and abs(scores[idx] - scores[order[pos - 1]]) < 1e-9:
                ranks[idx] = ranks[order[pos - 1]]
            else:
                ranks[idx] = pos + 1
        return ranks

    def hybrid_rerank_search(
        self,
        query: str,
        final_top_k: int = 3,
        rrf_k: int = 60,
        rough_top_k: int = 15,
        metadata_filter: Optional[Dict[str, Any]] = None,
        fuse_k: int = 10,
        rrf_weight: float = 0.6,
        rerank_weight: float = 0.4,
        reject_threshold: Optional[float] = None,
        rerank_granularity: str = "child",
        rewrite_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        端到端检索流水线：
        元数据过滤 -> Dense + BM25 双路召回 -> RRF 融合粗排 -> Rerank 交叉精排
        -> 按秩二次加权融合（reranker 排序稳定但绝对分漂移，取名次免疫分漂；
           召回侧稳定故加权 0.6 托底，精排侧 0.4 提供精度增益，小 k 增强名次区分度）
        -> 低置信拒答（可选）：全部候选的原始 rerank 最高分 < reject_threshold 时返回空结果

        rerank_granularity：
          - "child"：精排逐个子块打分，最终返回 Top-K 个子块（可能同属一张卡）；
          - "parent"：子块只负责召回，按父块(整卡)去重后对整卡全文精排，最终返回 Top-K 张卡。
            子块只是一个 150~300 字的小节，精排看不到整卡上下文，易被小节标题/字面带偏；
            父块精排让 Cross-Encoder 基于完整"现象-根因-处置"判断相关性。
            候选不带 parent_content（非父子切片策略）时自动退回 child。

        rewrite_query（可选，由 QueryRewriter 生成）：
          - 召回：原查询与改写查询各跑 BM25 + Dense，四路 RRF 融合（原查询保底，改写失败不致命）；
          - 精排：用改写查询打分——改写删掉了用户对原因的错误猜测，避免精排顺着猜测给兄弟卡高分。
        """
        t0 = time.time()

        # Step 1: 双路并行粗排召回
        bm25_res = self.bm25_search(query, top_k=rough_top_k, metadata_filter=metadata_filter)
        dense_res = self.dense_search(query, top_k=rough_top_k, metadata_filter=metadata_filter)

        # Step 1.5（可选）：改写查询再跑一组双路召回
        extra = []
        if rewrite_query and rewrite_query != query:
            extra = [self.bm25_search(rewrite_query, top_k=rough_top_k, metadata_filter=metadata_filter),
                     self.dense_search(rewrite_query, top_k=rough_top_k, metadata_filter=metadata_filter)]

        # Step 2: RRF 倒数排名融合（得到召回侧粗排名次）；多一组查询则候选上限同比放大
        fused_candidates = self.rrf_fusion(
            bm25_res, dense_res, rrf_k=rrf_k,
            candidate_limit=rough_top_k * (1 + len(extra) // 2), extra_results=extra
        )
        rerank_query = rewrite_query or query

        if not fused_candidates:
            return {"final_results": [], "bm25_count": 0, "dense_count": 0, "latency_ms": 0}

        # Step 2.5（父块精排）：按父块去重，每张卡由其 RRF 名次最高的子块代表，
        # 卡片顺序即卡级 RRF 名次；代表子块的 metadata 带 parent_content，下游回溯不变
        rerank_texts = None
        parent_mode = rerank_granularity == "parent" and all(
            "parent_content" in doc.metadata for doc, _ in fused_candidates
        )
        if parent_mode:
            seen_parents = set()
            card_candidates = []
            for doc, score in fused_candidates:
                pid = doc.metadata.get("parent_id") or doc.metadata.get("wiki_id")
                if pid in seen_parents:
                    continue
                seen_parents.add(pid)
                card_candidates.append((doc, score))
            fused_candidates = card_candidates
            rerank_texts = [doc.metadata["parent_content"] for doc, _ in fused_candidates]

        # Step 3: Cross-Encoder 深度交叉精排（得到精排名次）
        candidate_docs = [doc for doc, _ in fused_candidates]
        if rerank_texts is None:
            rerank_texts = [doc.page_content for doc in candidate_docs]
        pairs = [[rerank_query, txt] for txt in rerank_texts]
        rerank_scores = self.reranker.predict(pairs)

        # Step 4: 按秩二次加权融合
        # 说明：reranker 的"名次"比"绝对分"稳定（压测证实其绝对分区间会漂移，但排序基本不变）；
        # 召回侧 RRF 确定且正确，给更高权重(0.6)托底；小 k=10 让相邻名次的分数差更显著，
        # 这样即便精排偶尔把正确切片错后几名，召回侧的领先也能把它拉回 Top-K。
        rrf_ranks = list(range(1, len(fused_candidates) + 1))  # fused_candidates 已按 RRF 分降序
        rerank_ranks = self._ranks_of(rerank_scores)

        scored_docs = []
        for (doc, rrf_score), r_score, rrf_rank, rr_rank in zip(
            fused_candidates, rerank_scores, rrf_ranks, rerank_ranks
        ):
            fused_score = (rrf_weight / (fuse_k + rrf_rank)) + (rerank_weight / (fuse_k + rr_rank))
            scored_docs.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "rrf_score": round(rrf_score, 5),
                "rerank_score": round(r_score, 4),
                "rrf_rank": rrf_rank,
                "rerank_rank": rr_rank,
                "fused_score": round(fused_score, 6)
            })

        # 按融合分数倒序截取 Top-K
        final_results = sorted(scored_docs, key=lambda x: x["fused_score"], reverse=True)[:final_top_k]

        # Top-1/Top-2 双路共振保护：BM25 与 Dense 粗排各自前 2 名的"父块交集"代表
        # 召回侧高置信共振。HC-10 实测：Dense 第 1 / RRF 第 2 的目标卡被 Cross-Encoder
        # 误杀挤出 Top-3——召回两路都认可的候选，不允许被精排单点完全踢出。
        # 处理方式：用该父块融合分最高的子块替换掉最终列表中排名最低的非保护项
        # （不扩容，保持 top_k 不变；受保护项已在列时不重复插入）。
        def _top_parent_ids(res, n=2):
            seen: List[str] = []
            for doc, _, _ in res:
                pid = doc.metadata.get("parent_id") or doc.metadata.get("wiki_id")
                if pid and pid not in seen:
                    seen.append(pid)
                if len(seen) >= n:
                    break
            return set(seen)

        protected_parents = set.intersection(*[_top_parent_ids(r) for r in [bm25_res, dense_res] + extra])
        if protected_parents and final_results:
            def _pid_of(item: Dict[str, Any]) -> Optional[str]:
                md = item["metadata"]
                return md.get("parent_id") or md.get("wiki_id")

            final_parents = {_pid_of(d) for d in final_results}
            for pid in protected_parents - final_parents:
                best = max(
                    (d for d in scored_docs if _pid_of(d) == pid),
                    key=lambda d: d["fused_score"], default=None
                )
                if best is None:
                    continue
                # 从末尾向前找第一个非保护项作为替换对象
                victim_idx = next(
                    (i for i in range(len(final_results) - 1, -1, -1)
                     if _pid_of(final_results[i]) not in protected_parents),
                    None
                )
                if victim_idx is None:
                    continue
                rescued = dict(best)
                rescued["protected"] = True
                final_results[victim_idx] = rescued
                final_results.sort(key=lambda x: x["fused_score"], reverse=True)

        # 低置信拒答：按秩融合永远能排出 Top-K，库外问题也会硬塞 3 条最像的卡给 LLM。
        # 这里看的是精排给出的"原始绝对分"——名次只能说明谁更像，绝对分才说明像不像。
        # 只在本次打分全部来自远程 reranker 时生效：启发式兜底分的量纲不同，套用同一阈值会误杀
        # （注意要看"本次调用"是否降级，而不是服务整体是否可用——限流等瞬时故障只降级单次）。
        # ⚠️ 讲义第六篇记录过远程绝对分整体漂移，阈值需结合报告里的原始分分布定期复核。
        max_rerank = max(rerank_scores) if rerank_scores else 0.0
        rejected = (
            reject_threshold is not None
            and self.reranker.last_used_remote
            and max_rerank < reject_threshold
        )
        if rejected:
            final_results = []

        latency_ms = round((time.time() - t0) * 1000, 2)

        return {
            "final_results": final_results,
            "granularity": "parent" if parent_mode else "child",
            "rewrite_query": rewrite_query if extra else None,
            "rejected": rejected,
            "rerank_remote": self.reranker.last_used_remote,
            "max_rerank_score": round(max_rerank, 4),
            "scored_all": scored_docs,  # 全部候选的融合明细（供详细召回报告使用）
            "fused_count": len(fused_candidates),
            "bm25_count": len(bm25_res),
            "dense_count": len(dense_res),
            "latency_ms": latency_ms
        }


# ==============================================================================
# 3. 7 组命令、错误码、端口与跨分类冲突对抗评测集 (Golden Hard Benchmark)
# ==============================================================================

