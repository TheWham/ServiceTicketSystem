#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trace_retrieval.py — Day13 四轨检索过程追踪工具

把每道题在四个阶段的召回过程完整打印出来：
  ① BM25 字面召回  ② Dense 语义召回  ③ RRF 融合  ④ 全链路(+Rerank精排+按秩融合)

用法（在 D:\\day12\\demos 目录下）：
  python trace_retrieval.py                      # 跑内置 7 道对抗题
  python trace_retrieval.py --query "电脑蓝屏怎么办"   # 追踪自定义查询
  python trace_retrieval.py --k 5                # 每阶段展示 Top-5（默认 3）
"""

import sys
import argparse
from pathlib import Path

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from langchain_community.vectorstores import Chroma
from run_day12_pipeline import WikiStructureAwareChunker, KspEmbeddingProvider
from run_day13_pipeline import IndustrialHybridRetriever, HARD_BENCHMARK_SUITE
from rag_pipeline.config import load_config
from rag_pipeline.embedding import load_rerank_config


def build_retriever():
    """组装与 Day13 完全一致的混合检索器（切块器 + KSP embedding + BM25 + Reranker）"""
    chunker = WikiStructureAwareChunker()
    chunks = []
    for w in sorted(Path("output/wiki").glob("*.md")):
        if w.name == "_index.md":
            continue  # 目录导航页不入语料，避免污染检索
        chunks.extend(chunker.split_wiki_document(str(w)))

    emb = KspEmbeddingProvider(cache_dir="day12_output/.emb_cache")
    db = Chroma(
        persist_directory="day12_output/chroma_wiki_structured",
        embedding_function=emb,
        collection_name="wiki_structured_kb",
    )
    # 重排模型/后端与主链路同源（RERANK_* 或 KSP_*，及 pipeline.yaml 的 reranker.backend）
    cfg = load_config()
    reranker_model = load_rerank_config().get("model") or cfg.reranker_model
    return IndustrialHybridRetriever(vector_db=db, corpus_docs=chunks, reranker_model_name=reranker_model,
                                     reranker_backend=cfg.reranker_backend), chunks


def trace_one(retriever, chunks, query, expected=None, metadata_filter=None, k=3):
    """对单个查询打印四阶段召回过程与命中统计"""
    r = retriever
    expected = expected or []

    # ground truth：正文含多数黄金考点的卡片（仅用于对照展示）
    if expected:
        gt = sorted({c.metadata.get("wiki_id") for c in chunks
                     if sum(1 for f in expected if f in c.page_content) >= max(1, len(expected) // 2)})

    # ①② 双路召回（Top-k）
    bm = r.bm25_search(query, top_k=k, metadata_filter=metadata_filter)
    dn = r.dense_search(query, top_k=k, metadata_filter=metadata_filter)

    # ③ RRF 融合（先各召回 rough_top_k 再融合）
    rough = max(15, k)
    bm_full = r.bm25_search(query, top_k=rough, metadata_filter=metadata_filter)
    dn_full = r.dense_search(query, top_k=rough, metadata_filter=metadata_filter)
    fu = r.rrf_fusion(bm_full, dn_full, rrf_k=60, candidate_limit=k)

    # ④ 全链路（Rerank 精排 + 按秩加权融合）
    full = r.hybrid_rerank_search(query, final_top_k=k, metadata_filter=metadata_filter)["final_results"]

    def ids(docs):
        return [d.metadata.get("wiki_id", "?") for d in docs]

    print(f"\n  查询: {query}")
    if metadata_filter:
        print(f"  元数据过滤: {metadata_filter}")
    if expected:
        print(f"  正确答案卡片: {gt}")
        print(f"  黄金考点: {expected}")
    print(f"  ① BM25 召回 Top{k} : {ids([d for d, _, _ in bm])}")
    print(f"  ② Dense 召回 Top{k} : {ids([d for d, _, _ in dn])}")
    print(f"  ③ RRF 融合 Top{k}  : {ids([d for d, _ in fu])}")
    full_ids = [d["metadata"].get("wiki_id", "?") for d in full]
    fused_scores = [d["fused_score"] for d in full]
    print(f"  ④ 全链路 Top{k}    : {full_ids}   (融合分: {fused_scores})")

    if expected:
        ft = " ".join(d["content"] for d in full)
        hits = sum(1 for f in expected if f in ft)
        miss = [f for f in expected if f not in ft]
        print(f"  命中: {hits}/{len(expected)}  漏掉: {miss or '无'}")


def main():
    parser = argparse.ArgumentParser(description="Day13 四轨检索过程追踪")
    parser.add_argument("--query", default="", help="自定义查询（留空则跑内置 7 道题）")
    parser.add_argument("--k", type=int, default=3, help="每阶段展示 Top-K（默认 3）")
    args = parser.parse_args()

    print("🔧 正在组装混合检索器（加载向量库 + BM25 + Reranker）...")
    retriever, chunks = build_retriever()

    if args.query:
        print("=" * 78)
        print("🔍 自定义查询追踪")
        trace_one(retriever, chunks, args.query, expected=None, k=args.k)
    else:
        for test in HARD_BENCHMARK_SUITE:
            print("\n" + "=" * 78)
            print(f"[{test['id']}] {test['category']}")
            trace_one(
                retriever,
                chunks,
                test["query"],
                expected=test["expected_facts"],
                metadata_filter=test["filter"],
                k=args.k,
            )
    print("\n" + "=" * 78)
    print("✅ 完成")


if __name__ == "__main__":
    main()
