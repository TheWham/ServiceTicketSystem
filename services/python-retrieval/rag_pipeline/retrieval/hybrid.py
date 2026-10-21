"""工业级双路混合检索 + RRF 融合 + 按秩加权精排重排器。"""

import time
from typing import List, Dict, Any, Tuple, Optional

from ..chunking.structure_aware import Document

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

from .tokenizer import ChineseTokenizer, PurePythonBM25
from .reranker import KspReranker


class IndustrialHybridRetriever:
    """
    工业级混合检索与重排核心中枢：
    - 结构化语料库 BM25 倒排索引（带标点/停用词清洗与 0 分过滤）
      字面召回：对"工单号/错误码/端口/命令"等专有编号极强（IDF 高），
      恰好补上 Dense 向量检索把这些数字语义稀释掉的盲区；
    - Chroma 向量数据库语义检索
      语义召回：擅长意图匹配（"打不开网页"≈"无法访问网站"），与 BM25 字面召回互补；
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

    @staticmethod
    def _doc_key(doc: Document) -> str:
        """优先用唯一切片标识 child_id / chunk_id 作为 RRF 去重键，回退到 page_content。"""
        md = doc.metadata or {}
        return md.get("child_id") or md.get("chunk_id") or doc.page_content

    def bm25_search(
        self,
        query: str,
        top_k: int = 15,
        metadata_filter: Optional[Dict[str, Any]] = None,
        include_excluded: bool = False
    ) -> List[Tuple[Document, int, float]]:
        """BM25 关键词精确检索通道，返回 [(Doc, Rank, BM25_Score)]。

        注意：严格过滤 BM25_Score <= 0 的未命中文档，防止 0 分无关卡片按字典序混入 RRF 融合。

        include_excluded=True 时不套用 default_exclude——给「版本消歧」这类需要看见
        废止卡（判断它在某时刻是否有效）的调用方用。默认 False，行为与改前逐字一致。
        """
        tokenized_query = ChineseTokenizer.tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        rank = 1
        for idx in sorted_indices:
            if scores[idx] <= 0.0:
                break
            doc = self.corpus_docs[idx]
            if not include_excluded and self._is_excluded(doc.metadata):
                continue
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
        metadata_filter: Optional[Dict[str, Any]] = None,
        include_excluded: bool = False
    ) -> List[Tuple[Document, int, float]]:
        """Dense 语义向量检索通道，返回 [(Doc, Rank, Cosine_Similarity)]。

        include_excluded 语义同 bm25_search：为 True 时连废止卡一起召回。
        """
        if self.vector_db is None:
            return []

        apply_exclude = bool(self.default_exclude) and not include_excluded
        # 存在默认排除清单时先多取 3 倍再筛：防止被屏蔽卡占满 top_k 名额导致有效候选不足
        fetch_k = top_k * 3 if apply_exclude else top_k
        docs_with_scores = self.vector_db.similarity_search_with_relevance_scores(
            query, k=fetch_k, filter=metadata_filter
        )
        if apply_exclude:
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

        公式：RRF_Score(d) = Σ_channels 1/(rrf_k + rank_c(d))
        为什么用名次而非绝对分：BM25 分(0~30+)与余弦分(0~1)量纲完全不同，
        直接相加会被大数值淹没；名次天然归一，零调参即可无损合并两路。

        extra_results：额外通道（如改写查询的 BM25/Dense 结果），与前两路同权累加。
        """
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for doc, rank, _ in bm25_results:
            key = self._doc_key(doc)
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        for channel in [dense_results] + list(extra_results or []):
            for doc, rank, _ in channel:
                key = self._doc_key(doc)
                doc_map[key] = doc
                rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:candidate_limit]
        return [(doc_map[key], score) for key, score in sorted_candidates]

    @staticmethod
    def _ranks_of(scores: List[float]) -> List[int]:
        """把分数列表转成名次（1 = 最高），并列（分数相同）取相同名次。"""
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
        heuristic_reject_threshold: Optional[float] = 0.25,
        rerank_granularity: str = "child",
        rewrite_query: Optional[str] = None,
        gate: Optional[Dict[str, Any]] = None,
        include_excluded: bool = False,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """端到端检索流水线：元数据过滤 -> 双路召回 -> RRF 粗排 -> Rerank 精排 -> 按秩融合（可门控）-> 共振保护 -> 低置信拒答。

        gate：置信度动态门控参数（见 config.build_gate）。开启后按本次 rerank 打分分布切换
        Step 4 的融合权重——高置信放权精排翻盘、低置信/启发式降级时召回侧托底，解决
        "固定权重既怕精排误杀、又怕压制精排上限"的两难。默认 None = 固定权重（旧行为）。

        include_excluded：为 True 时双路召回都跳过 default_exclude，把废止卡也纳入候选。
        默认 False，行为与改前逐字一致。
        """
        t0 = time.time()

        def _brief(doc, w=90):
            t = " ".join(doc.page_content.split())
            return t[:w] + ("…" if len(t) > w else "")

        # Step 1: 双路并行粗排召回
        bm25_res = self.bm25_search(query, top_k=rough_top_k, metadata_filter=metadata_filter,
                                    include_excluded=include_excluded)
        dense_res = self.dense_search(query, top_k=rough_top_k, metadata_filter=metadata_filter,
                                      include_excluded=include_excluded)

        if verbose:
            print(f"\n{'=' * 72}")
            print(f"🔎 检索流程：{query}")
            print(f"{'=' * 72}")
            print(f"\n[① 向量检索] dense_search() —— Chroma 余弦相似度打分")
            print(f"    召回 {len(dense_res)} 个，Top-3：")
            for rank, (doc, _, score) in enumerate(dense_res[:3], 1):
                cid = doc.metadata.get("child_id") or doc.metadata.get("wiki_id", "?")
                print(f"      {rank}. [{cid}]  余弦分 {score:.4f}")
                print(f"         ↳ {_brief(doc)}")
            print(f"\n[② 全文检索] bm25_search() —— BM25 关键词打分")
            print(f"    召回 {len(bm25_res)} 个，Top-3：")
            for rank, (doc, _, score) in enumerate(bm25_res[:3], 1):
                cid = doc.metadata.get("child_id") or doc.metadata.get("wiki_id", "?")
                print(f"      {rank}. [{cid}]  BM25分 {score:.2f}")
                print(f"         ↳ {_brief(doc)}")

        # Step 1.5（可选）：改写查询再跑一组双路召回
        extra = []
        if rewrite_query and rewrite_query != query:
            extra = [self.bm25_search(rewrite_query, top_k=rough_top_k, metadata_filter=metadata_filter),
                     self.dense_search(rewrite_query, top_k=rough_top_k, metadata_filter=metadata_filter)]
            if verbose:
                print(f"\n[①' 改写查询] {rewrite_query}")
                print(f"    改写查询双路召回：BM25 {len(extra[0])} 个 / Dense {len(extra[1])} 个")

        # Step 2: RRF 倒数排名融合
        fused_candidates = self.rrf_fusion(
            bm25_res, dense_res, rrf_k=rrf_k,
            candidate_limit=rough_top_k * (1 + len(extra) // 2), extra_results=extra
        )
        rerank_query = rewrite_query or query

        if not fused_candidates:
            return {"final_results": [], "bm25_count": 0, "dense_count": 0, "latency_ms": 0}

        if verbose:
            print(f"\n[③ RRF 倒数排序] rrf_fusion() —— Σ 1/(60+名次)")
            print(f"    候选 {len(fused_candidates)} 个，Top-5：")
            for rank, (doc, score) in enumerate(fused_candidates[:5], 1):
                cid = doc.metadata.get("child_id") or doc.metadata.get("wiki_id", "?")
                print(f"      {rank}. [{cid}]  RRF分 {score:.5f}")
                print(f"         ↳ {_brief(doc)}")

        # Step 2.5（父块精排）：按父块去重
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
            if verbose:
                print(f"\n[③' 父块去重] 精排粒度=parent，候选 {len(fused_candidates)} 张卡（按整卡全文精排）")

        # Step 3: Cross-Encoder 深度交叉精排
        candidate_docs = [doc for doc, _ in fused_candidates]
        if rerank_texts is None:
            rerank_texts = [doc.page_content for doc in candidate_docs]
        pairs = [[rerank_query, txt] for txt in rerank_texts]
        rerank_scores = self.reranker.predict(pairs)

        if verbose:
            print(f"\n[④ Rerank 精排] KspReranker.predict() —— 交叉注意力打分")
            print(f"    {len(rerank_scores)} 个候选打分，Top-5（按精排分降序）：")
            sorted_rerank = sorted(zip(candidate_docs, rerank_scores), key=lambda x: x[1], reverse=True)
            for i, (doc, s) in enumerate(sorted_rerank[:5], 1):
                cid = doc.metadata.get("child_id") or doc.metadata.get("wiki_id", "?")
                print(f"      {i}. [{cid}]  rerank分 {s:.4f}")
                print(f"         ↳ {_brief(doc)}")

        # Step 4: 按秩二次加权融合
        # 为什么需要名次化：远程 Reranker 的绝对分会漂移（网关双后端分流，详见 reranker._parse_results），
        # 但排序基本稳定，取名次后融合对分数漂移免疫；召回侧稳定故 rrf_weight(0.6) 托底，
        # 精排侧 rerank_weight(0.4) 提供精度增益，小 fuse_k 增强名次区分度。
        #
        # 置信度动态门控（gate）：固定权重两头难顾——精排会误杀口语题（需 RRF 托底），
        # 但精排看准时又该放它翻盘登顶。改为按本次打分分布动态定权重：
        #   - 高置信（top-1 分够高 + 与 top-2 拉开 margin）→ 放权精排；
        #   - 低置信 / 启发式降级（rerank 没真跑）→ 召回侧托底。
        # 门控用 margin 而非绝对分做主要判据：同一次调用内两分数来自同一后端，共模漂移相减抵消；
        # 绝对分门槛只作粗筛（阈值须按本端点标定，见 pipeline.yaml gate_* 注释）。
        w_rrf_eff, w_rerank_eff = rrf_weight, rerank_weight
        gate_mode = "off"
        gate_margin = 0.0
        if gate and gate.get("enabled"):
            sorted_scores = sorted(rerank_scores, reverse=True)
            g_top1 = sorted_scores[0] if sorted_scores else 0.0
            gate_margin = (sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else 0.0
            confident = (
                self.reranker.last_used_remote
                and g_top1 >= gate.get("min_score", 0.55)
                and gate_margin >= gate.get("min_margin", 0.10)
            )
            if confident:
                gate_mode = "high"
                w_rrf_eff, w_rerank_eff = gate.get("conf_weights", (0.35, 0.65))
            else:
                gate_mode = "low"
                w_rrf_eff, w_rerank_eff = gate.get("low_weights", (0.65, 0.35))
            if verbose:
                print(f"\n[④' 置信度门控] {gate_mode} 模式 —— "
                      f"top1={g_top1:.4f} margin={gate_margin:.4f} "
                      f"(门槛 ≥{gate.get('min_score', 0.55)} / ≥{gate.get('min_margin', 0.10)}) "
                      f"→ 权重 RRF {w_rrf_eff} : Rerank {w_rerank_eff}")

        rrf_ranks = list(range(1, len(fused_candidates) + 1))
        rerank_ranks = self._ranks_of(rerank_scores)

        scored_docs = []
        for (doc, rrf_score), r_score, rrf_rank, rr_rank in zip(
            fused_candidates, rerank_scores, rrf_ranks, rerank_ranks
        ):
            fused_score = (w_rrf_eff / (fuse_k + rrf_rank)) + (w_rerank_eff / (fuse_k + rr_rank))
            scored_docs.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "rrf_score": round(rrf_score, 5),
                "rerank_score": round(r_score, 4),
                "rrf_rank": rrf_rank,
                "rerank_rank": rr_rank,
                "fused_score": round(fused_score, 6)
            })

        final_results = sorted(scored_docs, key=lambda x: x["fused_score"], reverse=True)[:final_top_k]

        # Top-1/Top-2 双路共振保护：
        # 修复旧版对 4 通道直接求全交集导致口语/改写题上保护失效的问题——
        # 只要父块在 BM25 侧（原查询或改写查询 Top-2）与 Dense 侧（原查询或改写查询 Top-2）同时命中，即视为双路共振
        def _top_parent_ids(res, n=2):
            seen: List[str] = []
            for doc, _, _ in res:
                pid = doc.metadata.get("parent_id") or doc.metadata.get("wiki_id")
                if pid and pid not in seen:
                    seen.append(pid)
                if len(seen) >= n:
                    break
            return set(seen)

        bm25_top_parents = _top_parent_ids(bm25_res)
        dense_top_parents = _top_parent_ids(dense_res)
        if len(extra) == 2:
            bm25_top_parents = bm25_top_parents | _top_parent_ids(extra[0])
            dense_top_parents = dense_top_parents | _top_parent_ids(extra[1])
        protected_parents = bm25_top_parents & dense_top_parents

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

        # 低置信拒答：远程用远端标定阈值（reject_threshold）；
        # 降级为启发式打分时用启发式阈值（heuristic_reject_threshold）。
        # 远程与启发式的分数尺度不同（启发式正样本 ≥0.47、无关问题 0.05~0.25），
        # 降级时若沿用远程阈值（或干脆因 last_used_remote=False 跳过拒答门），
        # 无关问题会被误当命中（网关 429 / 端点不可用时实测发生过）。
        threshold = (reject_threshold if self.reranker.last_used_remote
                     else heuristic_reject_threshold)
        max_rerank = max(rerank_scores) if rerank_scores else 0.0
        rejected = threshold is not None and max_rerank < threshold
        if rejected:
            final_results = []

        if verbose:
            print(f"\n[⑤ 按秩融合] {w_rrf_eff}/(10+RRF名次) + {w_rerank_eff}/(10+Rerank名次)"
                  + (f"（门控 {gate_mode}）" if gate_mode != "off" else ""))
            print(f"    最终 Top-{final_top_k}：")
            if final_results:
                for d in final_results:
                    cid = d["metadata"].get("child_id") or d["metadata"].get("wiki_id", "?")
                    mark = " 🛡" if d.get("protected") else ""
                    brief = " ".join(d["content"].split())
                    brief = brief[:90] + ("…" if len(brief) > 90 else "")
                    print(f"      [{cid}]  融合分 {d['fused_score']:.6f}  "
                          f"(RRF名次 {d['rrf_rank']} / Rerank名次 {d['rerank_rank']}){mark}")
                    print(f"         ↳ {brief}")
            else:
                print(f"      （低置信拒答：最高 rerank 分 {max_rerank:.4f} < 阈值 {threshold}）")
            print(f"{'=' * 72}")

        latency_ms = round((time.time() - t0) * 1000, 2)

        return {
            "final_results": final_results,
            "granularity": "parent" if parent_mode else "child",
            "rewrite_query": rewrite_query if extra else None,
            "rejected": rejected,
            "rerank_remote": self.reranker.last_used_remote,
            "max_rerank_score": round(max_rerank, 4),
            "gate_mode": gate_mode,
            "gate_margin": round(gate_margin, 4),
            "eff_weights": [w_rrf_eff, w_rerank_eff],
            "scored_all": scored_docs,
            "fused_count": len(fused_candidates),
            "bm25_count": len(bm25_res),
            "dense_count": len(dense_res),
            "latency_ms": latency_ms
        }
