#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_rerank_zero.py — 从真实完整链路复现「rerank 全 0」现象

不做任何玩具输入。装配路径与检索评测主流水线完全一致（复用同一套
config/chunker/embedding/Chroma/IndustrialHybridRetriever），用 HARD_BENCHMARK_SUITE
里的真实题目，对每题重复跑全链路 hybrid_rerank_search N 次，观察真实场景下
精排分数何时变成全 0（即 hybrid.py 里的 rerank_degraded）。

复现的是讲稿第五幕的机制：/rerank 端点间歇性「成功返回空 results」，
而调用失败会走启发式兜底（最低 0.05），永不为 0——所以 0 分 = 端点级间歇故障。

用法（在 D:\\day12\\demos 目录下）：
  python probe_rerank_zero.py                          # 全题集，每题重复 5 次
  python probe_rerank_zero.py --n 20                   # 每题重复 20 次（更易撞上）
  python probe_rerank_zero.py --ids HC-04 HC-07        # 只跑指定题
  python probe_rerank_zero.py --delay 0.2              # 每次调用间隔（防限流）
"""

import sys
import argparse
import json
import time
from pathlib import Path

# 脚本位于 tools/，向上定位仓库根并加入 sys.path，便于 import rag_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from rag_pipeline.config import load_config, build_chunker, WIKI_DIR, INDEXING_OUTPUT, load_rerank_config
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.evaluation.suite import HARD_BENCHMARK_SUITE


def build_retriever():
    """照搬检索评测主流水线的装配逻辑：config -> 切块 -> 嵌入 -> Chroma -> 混合检索器。"""
    cfg = load_config()
    reranker_model = load_rerank_config().get("model") or cfg.reranker_model
    project_root = Path(__file__).resolve().parent.parent
    wiki_path = WIKI_DIR
    chroma_path = INDEXING_OUTPUT / "chroma_wiki_structured"

    print(f"[1/3] 载入知识基座与向量库 ...")
    chunker, use_parent_child = build_chunker(cfg)
    embed_provider = KspEmbeddingProvider(cache_dir=str(project_root / cfg.embedding_cache_dir))
    print(f"      -> Embedding: {embed_provider.engine_type}")

    wiki_files = sorted(wiki_path.glob("*.md"))
    wiki_files = [f for f in wiki_files if f.name != "_index.md"]
    if not wiki_files:
        raise FileNotFoundError(f"未在 {wiki_path} 找到 Wiki 卡片，请先跑清洗/建库流水线")

    all_chunks: list = []
    for wf in wiki_files:
        if use_parent_child:
            _p, children = chunker.split_wiki_document(str(wf))
            all_chunks.extend(children)
        else:
            all_chunks.extend(chunker.split_wiki_document(str(wf)))
    print(f"      -> Wiki 卡片 {len(wiki_files)} 篇 → 切片 {len(all_chunks)} 块"
          f"{'（父子·子块）' if use_parent_child else ''}")

    # 语料一致性校验（同主流水线）：manifest 指纹不一致则重建内存索引
    stale_reason = None
    manifest_file = chroma_path / "manifest.json"
    if chroma_path.exists() and compute_wiki_fingerprint is not None:
        if not manifest_file.exists():
            stale_reason = "无 manifest"
        else:
            try:
                saved = json.loads(manifest_file.read_text(encoding="utf-8"))
                if saved.get("wiki_fingerprint") != compute_wiki_fingerprint(wiki_files):
                    stale_reason = "Wiki 卡片内容已变更"
                elif saved.get("config_fingerprint") and \
                        saved["config_fingerprint"] != cfg_fingerprint(cfg):
                    stale_reason = "切片配置已变更"
            except Exception as e:
                stale_reason = f"manifest 读取失败({e})"

    if chroma_path.exists() and stale_reason is None:
        try:
            vector_db = Chroma(persist_directory=str(chroma_path),
                               embedding_function=embed_provider,
                               collection_name="wiki_structured_kb")
            print(f"      -> 加载持久化 Chroma 成功：{chroma_path.name}")
        except Exception as e:
            print(f"      ⚠️ 加载持久化 Chroma 警告({e})，重建内存索引")
            vector_db = Chroma.from_documents(all_chunks, embed_provider, collection_name="wiki_structured_kb")
    else:
        if stale_reason:
            print(f"      ⚠️ 向量库与语料不一致（{stale_reason}），重建内存索引")
        vector_db = Chroma.from_documents(all_chunks, embed_provider, collection_name="wiki_structured_kb")

    print(f"[2/3] 装配 IndustrialHybridRetriever ...")
    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=all_chunks,
        reranker_model_name=reranker_model,
        default_exclude=cfg.retrieval.default_exclude,
    )
    return retriever, cfg


def cfg_fingerprint(cfg):
    from rag_pipeline.config import config_fingerprint
    return config_fingerprint(cfg)


def run_one_round(retriever, test, rc):
    """对单题跑一次全链路，返回 (rerank 分数列表, 是否退化, 是否全 0)。"""
    res = retriever.hybrid_rerank_search(
        query=test["query"],
        final_top_k=rc.top_k,
        rrf_k=rc.rrf_k,
        rough_top_k=rc.rough_top_k,
        fuse_k=rc.fuse_k,
        rrf_weight=rc.rrf_weight,
        rerank_weight=rc.rerank_weight,
        metadata_filter=test["filter"],
    )
    scored = res.get("scored_all", [])
    rerank_scores = [d["rerank_score"] for d in scored]
    degraded = res.get("rerank_degraded", False)
    all_zero = bool(rerank_scores) and all(abs(s) < 1e-9 for s in rerank_scores)
    return rerank_scores, degraded, all_zero


def main():
    parser = argparse.ArgumentParser(description="真实完整链路复现 rerank 全 0 现象")
    parser.add_argument("--n", type=int, default=5, help="每题重复跑全链路的次数")
    parser.add_argument("--ids", nargs="*", default=None, help="只跑指定题号（如 HC-04 HC-07）")
    parser.add_argument("--delay", type=float, default=0.1, help="每次调用间隔秒数")
    args = parser.parse_args()

    retriever, cfg = build_retriever()
    rc = cfg.retrieval
    suite = [t for t in HARD_BENCHMARK_SUITE if not args.ids or t["id"] in args.ids]
    if not suite:
        print("❌ 没有匹配的题目")
        sys.exit(1)

    print(f"[3/3] 对 {len(suite)} 题 × {args.n} 次全链路，观察 rerank 分数 ...\n")

    grand_zero = 0
    grand_total = 0
    per_test = []

    for test in suite:
        qid, target = test["id"], test.get("target_id")
        print(f"【{qid}】{test['query'][:38]}…  (目标卡 {target or '—'})")
        zero_rounds = 0
        for i in range(1, args.n + 1):
            grand_total += 1
            try:
                scores, degraded, all_zero = run_one_round(retriever, test, rc)
            except Exception as e:
                print(f"     第{i:3d}次  异常：{e}")
                continue
            if all_zero:
                zero_rounds += 1
                grand_zero += 1
                print(f"     第{i:3d}次  ⚠️ rerank 全 0  scores={scores}  degraded={degraded}")
            else:
                print(f"     第{i:3d}次  rerank={[round(s,4) for s in scores]}")
            if args.delay > 0:
                time.sleep(args.delay)
        per_test.append((qid, zero_rounds))
        print()

    print("=" * 72)
    print(f"汇总（{len(suite)} 题 × {args.n} 次 = {grand_total} 次全链路调用）")
    for qid, z in per_test:
        print(f"  {qid}: 全 0 {z} 次")
    print(f"  → 共 {grand_zero} 次 rerank 全 0（占 {100*grand_zero/max(grand_total,1):.1f}%）")
    print("\n说明：全 0 是 /rerank 端点「成功返回空 results」的间歇故障；")
    print("      调用失败走启发式兜底(最低 0.05)永不 0，故 0 分与 query/候选内容无关。")


if __name__ == "__main__":
    main()
