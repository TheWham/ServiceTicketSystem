#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_golden_margin.py — 黄金集"全 100%"的三项 falsification 探针。

背景：Day14 基线四项指标全 100%，需排除"指标饱和"旧病复发。本探针回答：
  ① 自证度：12 道标准题里，query 自带 expected_keyword 词面的有几道（BM25 必中=自证）；
  ② 冲突 100% 的来源：关闭 default_exclude 后，废止卡是否侵入 Top-3
     （侵入=该指标测的是元数据过滤器而非模型消歧能力，100% 属机制自证）；
  ③ 拒答裕度：生产配置（parent 粒度+查询改写）下正/负样本 top-1 rerank 分分布，
     与 yaml reject_threshold=0.40 的间距（裕度过窄=100% 是走钢丝）。

用法：python tools/probe_golden_margin.py
"""

import sys
import json
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from langchain_community.vectorstores import Chroma

from rag_pipeline.config import load_config
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.retrieval.query_rewriter import QueryRewriter
import run_day14_pipeline as d14

DEPRECATED = ("已废止", "已下线")


def main():
    cfg = load_config()
    rc = cfg.retrieval
    golden = json.loads((REPO_ROOT / "evals" / "golden_dataset_v1.0.json").read_text(encoding="utf-8"))

    # ---- ① 自证度静态分析（无 API 调用）----
    print("=" * 78)
    print("① 标准题自证度分析（query 是否自带答案词面）")
    print("=" * 78)
    self_evident = []
    for item in golden:
        if item["is_adversarial"] or item["is_conflict_check"]:
            continue
        leaked = [k for k in item["expected_keywords"] if k.lower() in item["query"].lower()]
        tag = "自证" if leaked else "改写"
        if leaked:
            self_evident.append(item["id"])
        print(f"  {item['id']} [{tag}] 泄漏词面: {leaked if leaked else '无'}")
    n_std = sum(1 for i in golden if not i["is_adversarial"] and not i["is_conflict_check"])
    print(f"  → 标准题 {n_std} 道中自证 {len(self_evident)} 道、纯改写 {n_std - len(self_evident)} 道")

    # ---- 装配生产检索器 ----
    wiki_path = REPO_ROOT / "artifacts" / "output" / "wiki"
    chroma_path = REPO_ROOT / "artifacts" / "indexing" / "chroma_wiki_structured"
    corpus = d14.load_corpus_with_deterministic_ids(wiki_path, cfg)
    embed = KspEmbeddingProvider(cache_dir=str(REPO_ROOT / cfg.embedding_cache_dir))
    vector_db = Chroma(persist_directory=str(chroma_path), embedding_function=embed,
                       collection_name=cfg.store_collection)
    retriever = IndustrialHybridRetriever(vector_db=vector_db, corpus_docs=corpus,
                                          reranker_model_name=cfg.reranker_model,
                                          default_exclude=rc.default_exclude)
    rewriter = QueryRewriter(model=rc.rewrite_model,
                             cache_dir=str(REPO_ROOT / "artifacts" / "evaluation" / ".llm_cache" / "rewrite")) \
        if rc.query_rewrite else None

    def search(r, q):
        rewrite = rewriter.rewrite(q) if rewriter else None
        return r.hybrid_rerank_search(
            query=q, final_top_k=rc.top_k, rrf_k=rc.rrf_k, rough_top_k=rc.rough_top_k,
            fuse_k=rc.fuse_k, rrf_weight=rc.rrf_weight, rerank_weight=rc.rerank_weight,
            reject_threshold=None, heuristic_reject_threshold=None,  # 探针要看原始分，临时关闭物理拒答（含降级路径）
            rerank_granularity=rc.rerank_granularity, rewrite_query=rewrite)

    # ---- ③ 拒答裕度：正/负样本 top-1 原始 rerank 分分布 ----
    print()
    print("=" * 78)
    print(f"③ 拒答裕度分析（生产配置 parent+rewrite，reject 临时关闭；yaml 阈值 {rc.reject_threshold}）")
    print("=" * 78)
    pos, neg = [], []
    for item in golden:
        res = search(retriever, item["query"])
        score = res["max_rerank_score"]
        (neg if item["is_adversarial"] else pos).append((item["id"], score))
    pos.sort(key=lambda x: x[1])
    neg.sort(key=lambda x: -x[1])
    print("  正样本（升序，最弱在前）:")
    for qid, s in pos[:5]:
        print(f"    {qid}: {s:.4f}")
    print("  负样本（降序，最强在前）:")
    for qid, s in neg:
        print(f"    {qid}: {s:.4f}")
    thr = rc.reject_threshold or 0.40
    margin_pos = min(s for _, s in pos) - thr
    margin_neg = thr - max(s for _, s in neg)
    print(f"  → 阈值 {thr:.4f}：正样本侧裕度 {margin_pos:+.4f}（最弱正样本 - 阈值），"
          f"负样本侧裕度 {margin_neg:+.4f}（阈值 - 最强负样本）")
    if margin_pos < 0.05 or margin_neg < 0.05:
        print("  ⚠️ 任一侧裕度 < 0.05：拒答 100% 属窄margin状态，端点分数稍漂即翻转")

    # ---- ② 冲突 100% 来源：关闭过滤后废止卡是否侵入 ----
    print()
    print("=" * 78)
    print("② 冲突消歧 falsification（关闭 default_exclude，看废止卡是否侵入 Top-3）")
    print("=" * 78)
    retriever_nofilter = IndustrialHybridRetriever(vector_db=vector_db, corpus_docs=corpus,
                                                   reranker_model_name=cfg.reranker_model,
                                                   default_exclude={})
    invaded = 0
    for item in golden:
        if not item["is_conflict_check"]:
            continue
        res = search(retriever_nofilter, item["query"])
        parents = [(d["metadata"].get("parent_id") or d["metadata"].get("wiki_id"),
                    d["metadata"].get("wiki_status")) for d in res["final_results"]]
        dep = [p for p, st in parents if st in DEPRECATED or (p or "").startswith("ITKB-LEG")]
        if dep:
            invaded += 1
        print(f"  {item['id']}: Top-3 父块 {[p for p, _ in parents]} → 废止卡侵入: {dep or '无'}")
    n_conf = sum(1 for i in golden if i["is_conflict_check"])
    print(f"  → 无过滤时 {invaded}/{n_conf} 道冲突题被废止卡侵入："
          f"{'冲突 100% 来自元数据过滤（机制自证），非模型消歧能力' if invaded else '模型自身也能消歧'}")


if __name__ == "__main__":
    main()
