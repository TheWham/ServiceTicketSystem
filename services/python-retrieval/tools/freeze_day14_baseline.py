#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
freeze_day14_baseline.py — 固化 Day14 黄金集检索基线（服务化回归的对照真源）

以与 rag_service 服务完全一致的装配路径（evaluation.py 的 retriever 装配 +
确定性 chunk_id 语料）跑 evals/golden_dataset_v1.0.json 全部 20 题，
把每题的命中父卡集合 / 拒答标记 / top-1 rerank 分 / 时延冻结为 JSON，供
tools/run_service_regression.py 逐题比对 HTTP 服务端点的行为一致性。

用法（在 D:\\day12\\demos 目录下）：
    python tools/freeze_day14_baseline.py
    python tools/freeze_day14_baseline.py --output artifacts/evals/day14_baseline.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

# 脚本位于 tools/，向上定位仓库根并加入 sys.path，便于 import rag_pipeline
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")

try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    Chroma = None

from rag_pipeline.config import load_config, config_fingerprint, build_gate
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.chunking.corpus import load_corpus_with_deterministic_ids
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.retrieval.query_rewriter import QueryRewriter
from rag_pipeline.evaluation.golden import GoldenSetEvaluator


def main():
    parser = argparse.ArgumentParser(description="固化 Day14 黄金集检索基线")
    parser.add_argument("--wiki-dir", default="artifacts/output/wiki")
    parser.add_argument("--chroma-dir", default="artifacts/indexing/chroma_wiki_structured")
    parser.add_argument("--golden-dataset", default="evals/golden_dataset_v1.0.json")
    parser.add_argument("--output", default="artifacts/evals/day14_baseline.json")
    args = parser.parse_args()

    cfg = load_config()
    rc = cfg.retrieval
    wiki_path = REPO_ROOT / args.wiki_dir
    chroma_path = REPO_ROOT / args.chroma_dir
    golden_path = REPO_ROOT / args.golden_dataset
    out_path = REPO_ROOT / args.output

    print("[1/3] 提取 Wiki 切片语料并绑定确定性 chunk_id ...")
    corpus_docs = load_corpus_with_deterministic_ids(wiki_path, cfg)
    print(f"       -> 语料 {len(corpus_docs)} 个 Chunks")

    print("[2/3] 装配混合检索与重排核心（与服务侧 assembly 同参：reranker_backend 显式传入）...")
    embed_provider = KspEmbeddingProvider(cache_dir=str(REPO_ROOT / cfg.embedding_cache_dir))
    vector_db = None
    manifest_file = chroma_path / "manifest.json"
    stale_reason = None
    if Chroma is not None and chroma_path.exists():
        if not manifest_file.exists():
            stale_reason = "无 manifest（旧版本向量库）"
        else:
            saved = json.loads(manifest_file.read_text(encoding="utf-8"))
            wiki_files = sorted(p for p in wiki_path.glob("*.md") if p.name != "_index.md")
            if saved.get("wiki_fingerprint") != compute_wiki_fingerprint(wiki_files):
                stale_reason = "Wiki 卡片内容已变更"
            elif saved.get("config_fingerprint") and saved["config_fingerprint"] != config_fingerprint(cfg):
                stale_reason = "切片配置已变更（configs/pipeline.yaml）"
        if stale_reason is None:
            vector_db = Chroma(persist_directory=str(chroma_path),
                               embedding_function=embed_provider,
                               collection_name=cfg.store_collection)
            print(f"       -> 成功加载持久化向量数据库：{chroma_path.name}")
    if vector_db is None:
        raise RuntimeError(f"❌ 持久化向量库不可用（{stale_reason or '未安装 chromadb'}），基线必须基于真实持久库，拒绝内存重建")

    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=corpus_docs,
        reranker_model_name=cfg.reranker_model,
        default_exclude=cfg.retrieval.default_exclude,
        reranker_backend=cfg.reranker_backend,
    )

    rewriter = QueryRewriter(
        model=rc.rewrite_model,
        cache_dir=str(REPO_ROOT / "artifacts/evaluation/.llm_cache/rewrite"),
    ) if rc.query_rewrite else None
    if rewriter:
        print(f"       -> 查询改写已启用：{rewriter.model}（磁盘缓存复用 Day14）")

    print(f"[3/3] 跑黄金集 {args.golden_dataset} 全量 20 题（远程 rerank，需数分钟）...")
    evaluator = GoldenSetEvaluator(retriever=retriever, golden_dataset_path=str(golden_path),
                             rc=rc, rewriter=rewriter)
    t0 = time.time()
    summary = evaluator.run_evaluation(top_k=rc.top_k)
    wall_s = round(time.time() - t0, 1)

    baseline = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "wall_seconds": wall_s,
        "golden_dataset": args.golden_dataset,
        "wiki_fingerprint": compute_wiki_fingerprint(
            sorted(p for p in wiki_path.glob("*.md") if p.name != "_index.md")),
        "config_fingerprint": config_fingerprint(cfg),
        "reranker_model": cfg.reranker_model,
        "reranker_backend": cfg.reranker_backend,
        "top_k": rc.top_k,
        "reject_threshold": rc.reject_threshold,
        "rerank_backend_stats": retriever.reranker.backend_stats,
        "summary_metrics": {
            "hit_rate_top1": summary["hit_rate_top1"],
            f"hit_rate_top{rc.top_k}": summary[f"hit_rate_top{rc.top_k}"],
            "mrr": summary["mrr"],
            "conflict_accuracy": summary["conflict_accuracy"],
            "adversarial_refusal_rate": summary["adversarial_refusal_rate"],
            "avg_latency_ms": summary["avg_latency_ms"],
        },
        "results": [
            {
                "id": d["id"],
                "query": d["query"],
                "category": d["category"],
                "is_adversarial": d["is_adversarial"],
                "is_conflict": d["is_conflict"],
                "parent_ids": d["parent_ids"],
                "rejected": d["rejected"],
                "refused": d["rejected"],
                "hit_rank": d["hit_rank"],
                "top_score": d["top_score"],
                "gate_mode": d["gate_mode"],
                "latency_ms": round(d["latency"], 1),
            }
            for d in summary["details"]
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n🎉 基线已冻结至：{out_path}（{len(baseline['results'])} 题，耗时 {wall_s}s）")


if __name__ == "__main__":
    main()
