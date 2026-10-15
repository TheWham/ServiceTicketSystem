"""检索评测主流水线（四轨对比评测 + 报告落盘）：四轨统一父卡 Top-K 口径对比评测。"""

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..chunking.structure_aware import Document
from ..store import SimpleVectorStore

try:
    from langchain_community.vectorstores import Chroma
    import chromadb
except ImportError:
    Chroma = None
    chromadb = None

from ..config import load_config, config_fingerprint, build_chunker, load_rerank_config, build_gate
from ..embedding import KspEmbeddingProvider
from ..chunking.parent_child import expand_to_parents
from ..chunking.fingerprint import compute_wiki_fingerprint
from ..retrieval.hybrid import IndustrialHybridRetriever
from ..retrieval.query_rewriter import QueryRewriter
from ..evaluation.suite import HARD_BENCHMARK_SUITE, DEV_SUITE, TEST_SUITE
from ..evaluation.report import (
    _generate_markdown_report, _generate_retrieval_detail_report, pick_winners, suite_breakdown
)


class _Tee:
    """把 stdout 同时写入控制台与日志文件，便于把完整运行过程落盘。"""

    def __init__(self, stdout, file):
        self.stdout = stdout
        self.file = file

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def run_evaluation():
    """检索评测主流水线：载入语料/向量库 -> 装配混合检索器 -> 四轨评测 -> 报告。

    四轨对比（同一道题跑四条链路，统一以 rough_top_k 召回子块并回溯去重取 Top-K 父卡，消除口径偏差）：
      A 纯 Dense 向量检索
      B 纯 BM25 关键词检索
      C Dense + BM25 + RRF 融合（无精排）
      D 全链路：元数据过滤 + 双路召回 + RRF + Rerank 精排 + 按秩融合兜底
    """
    parser = argparse.ArgumentParser(description="混合检索与 Rerank 重排评测流水线")
    parser.add_argument("--wiki-dir", default="artifacts/output/wiki", help="Wiki 卡片目录")
    parser.add_argument("--chroma-dir", default="artifacts/indexing/chroma_wiki_structured", help="结构化向量库目录")
    parser.add_argument("--output-dir", default="artifacts/evaluation", help="评测产物输出目录")
    parser.add_argument("--reranker", default="", help="重排模型名称(默认取 RERANK_MODEL > pipeline.yaml)")
    parser.add_argument("--suite", choices=["main", "dev", "holdout", "test"], default="main",
                        help="main=主题集；dev=开发集（holdout 为旧名）——二者用于调参/标定；"
                             "test=封存测试集，只在方案定稿后运行一次。dev/test 报告加后缀另存")
    parser.add_argument("--reject-threshold", type=float, default=None,
                        help="临时覆盖 pipeline.yaml 的 reject_threshold（换模型对比用，不改配置文件）")
    parser.add_argument("--rewrite-model", default=None,
                        help="临时覆盖 pipeline.yaml 的 rewrite_model；传 none 关闭查询改写（对照实验用）")
    parser.add_argument("--verbose", action="store_true", help="打印每题全链路检索的详细过程日志（双路召回/RRF/Rerank/融合）")
    parser.add_argument("--log-file", default="artifacts/evaluation/评测运行日志.md",
                        help="运行日志落盘路径（把控制台输出同时写入该文件；传空字符串则不写）")
    args = parser.parse_args()

    if args.log_file:
        import sys
        log_path = Path(args.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = _Tee(sys.stdout, open(log_path, "w", encoding="utf-8"))
    if args.suite == "holdout":
        args.suite = "dev"
    suite = {"main": HARD_BENCHMARK_SUITE, "dev": DEV_SUITE, "test": TEST_SUITE}[args.suite]
    suffix = {"main": "", "dev": "_开发集", "test": "_测试集"}[args.suite]

    cfg = load_config()
    reranker_model = args.reranker or load_rerank_config().get("model") or cfg.reranker_model

    print("=" * 80)
    print("🚀 双路混合检索与 Rerank 深度重排评测流水线")
    print("=" * 80)

    project_root = Path(__file__).resolve().parents[2]
    wiki_path = project_root / args.wiki_dir
    chroma_path = project_root / args.chroma_dir
    out_path = project_root / args.output_dir
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/4] 载入知识基座切片语料与 Chroma 向量数据库...")

    chunker, use_parent_child = build_chunker(cfg)

    if KspEmbeddingProvider is not None:
        embed_provider = KspEmbeddingProvider(cache_dir=str(project_root / cfg.embedding_cache_dir))
        print(f"       -> Embedding 引擎: 【{embed_provider.engine_type}】")
    else:
        embed_provider = None
        print("       ⚠️ 未复用到 KspEmbeddingProvider，Dense 通道可能不可用")

    wiki_files = sorted(wiki_path.glob("*.md")) if wiki_path.exists() else []
    wiki_files = [f for f in wiki_files if f.name != "_index.md"]
    if not wiki_files:
        raise FileNotFoundError(f"❌ 未在 {wiki_path} 找到 Wiki 卡片，请先运行 Day 11 流水线！")

    all_chunks: List[Document] = []
    for wf in wiki_files:
        if use_parent_child:
            _parent, children = chunker.split_wiki_document(str(wf))
            all_chunks.extend(children)
        else:
            all_chunks.extend(chunker.split_wiki_document(str(wf)))

    print(f"       -> 成功提取 Wiki 切片语料共：{len(all_chunks)} 个"
          f"{'（父子切片·子块）' if use_parent_child else ''} Chunks")

    stale_reason = None
    manifest_file = chroma_path / "manifest.json"
    if chroma_path.exists() and compute_wiki_fingerprint is not None:
        if not manifest_file.exists():
            stale_reason = "无 manifest（旧版本向量库）"
        else:
            try:
                saved = json.loads(manifest_file.read_text(encoding="utf-8"))
                if saved.get("wiki_fingerprint") != compute_wiki_fingerprint(wiki_files):
                    stale_reason = "Wiki 卡片内容已变更"
                elif saved.get("config_fingerprint"):
                    if saved["config_fingerprint"] != config_fingerprint(cfg):
                        stale_reason = "切片配置已变更（configs/pipeline.yaml）"
                elif saved.get("chunker") != {"name": cfg.chunking.strategy, "child_size": cfg.chunking.child_size}:
                    stale_reason = "切块参数已变更（旧版 manifest）"
            except Exception as e:
                stale_reason = f"manifest 读取失败({e})"

    vector_db = None
    if Chroma is not None and chroma_path.exists() and stale_reason is None:
        try:
            vector_db = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=embed_provider,
                collection_name="wiki_structured_kb"
            )
            print(f"       -> 成功加载持久化向量数据库：{chroma_path.name}")
        except Exception as e:
            print(f"       ⚠️ 加载持久化 Chroma 遇到警告 ({e})，正在自动重建内存索引...")
            vector_db = Chroma.from_documents(
                documents=all_chunks,
                embedding=embed_provider,
                collection_name="wiki_structured_kb"
            )
    elif Chroma is not None:
        if stale_reason:
            print(f"       ⚠️ 持久化向量库与当前语料不一致（{stale_reason}），自动重建内存索引...")
        vector_db = Chroma.from_documents(
            documents=all_chunks,
            embedding=embed_provider,
            collection_name="wiki_structured_kb"
        )
    else:
        # 环境未安装 chromadb 时，优先从 chroma.sqlite3 直接加载真实 4096 维向量，否则构建内存向量库
        if chroma_path.exists() and stale_reason is None:
            vector_db = SimpleVectorStore.from_chroma_sqlite(str(chroma_path), embed_provider)
        if vector_db is None:
            vector_db = SimpleVectorStore.from_documents(all_chunks, embed_provider)

    print(f"\n[2/4] 初始化装配 IndustrialHybridRetriever 混合检索与重排核心...")
    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=all_chunks,
        reranker_model_name=reranker_model,
        default_exclude=cfg.retrieval.default_exclude,
        reranker_backend=cfg.reranker_backend
    )

    suite_name = {"main": "主题集", "dev": "开发集", "test": "测试集（封存，定稿后只运行一次）"}[args.suite]
    print(f"\n[3/4] 执行{suite_name} {len(suite)} 组对抗评测：{suite_breakdown(suite)}（四轨对比大比武）...")
    rc = cfg.retrieval
    if args.reject_threshold is not None:
        rc.reject_threshold = args.reject_threshold
    if args.rewrite_model is not None:
        rc.query_rewrite = args.rewrite_model.lower() != "none"
        rc.rewrite_model = "" if args.rewrite_model.lower() == "none" else args.rewrite_model
    rewriter = QueryRewriter(model=rc.rewrite_model, cache_dir=str(out_path / ".llm_cache" / "rewrite")) if rc.query_rewrite else None
    if rewriter:
        print(f"       -> 查询改写已启用：{rewriter.model}（磁盘缓存 {out_path.name}/.llm_cache/rewrite）")
    eval_records = []

    for test in suite:
        qid = test["id"]
        query = test["query"]
        expected = test["expected_facts"]
        m_filter = test["filter"]
        target_id = test.get("target_id")
        trap_ids = test.get("trap_ids", [])

        def _track_metrics(parents):
            ids = [d.metadata.get("wiki_id") for d in parents]
            rank = (ids.index(target_id) + 1) if (target_id and target_id in ids) else None
            if target_id:
                tgt_text = next((d.page_content for d in parents
                                 if d.metadata.get("wiki_id") == target_id), "")
                hits = sum(1 for f in expected if f in tgt_text)
            else:
                hits = 0
            false_recall = bool(set(ids) & set(trap_ids))
            return ids, rank, hits, false_recall

        # 修复四轨口径不对称：父子切片下每张卡含 ~4 个子块，若只召回 top_k=3 个子块，
        # 同卡的 3 个子块会占满全部名额导致回溯后只有 1 张父卡。
        # 因此轨 1 / 轨 2 / 轨 3 统一先召回 rough_top_k (15) 个候选子块，回溯父块去重后再取前 top_k (3) 张父卡！
        fetch_k = rc.rough_top_k if use_parent_child else rc.top_k

        # 轨 1: 纯 Dense 向量检索
        t0 = time.time()
        dense_rough = retriever.dense_search(query, top_k=fetch_k, metadata_filter=m_filter)
        dense_time = round((time.time() - t0) * 1000, 1)
        dense_raw = dense_rough[:rc.top_k]
        dense_parents = (expand_to_parents([d for d, _, _ in dense_rough]) if expand_to_parents else [d for d, _, _ in dense_rough])[:rc.top_k]
        dense_ids, dense_rank, dense_hits, dense_false = _track_metrics(dense_parents)

        # 轨 2: 纯 BM25 关键词检索
        t0 = time.time()
        bm25_rough = retriever.bm25_search(query, top_k=fetch_k, metadata_filter=m_filter)
        bm25_time = round((time.time() - t0) * 1000, 1)
        bm25_raw = bm25_rough[:rc.top_k]
        bm25_parents = (expand_to_parents([d for d, _, _ in bm25_rough]) if expand_to_parents else [d for d, _, _ in bm25_rough])[:rc.top_k]
        bm25_ids, bm25_rank, bm25_hits, bm25_false = _track_metrics(bm25_parents)

        # 轨 3: Dense + BM25 双路粗排 (Top-15) + RRF 融合 -> 回溯去重取 Top-3 父卡
        t0 = time.time()
        fused_all = retriever.rrf_fusion(bm25_rough, dense_rough, rrf_k=rc.rrf_k, candidate_limit=fetch_k)
        fusion_time = round((time.time() - t0) * 1000, 1)
        fused_time = round(dense_time + bm25_time + fusion_time, 1)
        fused = fused_all[:rc.top_k]
        fused_parents = (expand_to_parents([d for d, _ in fused_all]) if expand_to_parents else [d for d, _ in fused_all])[:rc.top_k]
        fused_ids, fused_rank, fused_hits, fused_false = _track_metrics(fused_parents)

        # 轨 4: 顶级工业级全链路
        t0 = time.time()
        rewrite = rewriter.rewrite(query) if rewriter else None
        rewrite_ms = round((time.time() - t0) * 1000, 1)
        full_res = retriever.hybrid_rerank_search(
            query=query,
            final_top_k=rc.top_k,
            rrf_k=rc.rrf_k,
            rough_top_k=rc.rough_top_k,
            fuse_k=rc.fuse_k,
            rrf_weight=rc.rrf_weight,
            rerank_weight=rc.rerank_weight,
            metadata_filter=m_filter,
            reject_threshold=rc.reject_threshold,
            rerank_granularity=rc.rerank_granularity,
            rewrite_query=rewrite,
            gate=build_gate(rc),
            verbose=args.verbose
        )
        full_docs = full_res["final_results"]
        full_parents = (expand_to_parents(full_docs) if expand_to_parents else [Document(page_content=d["content"], metadata=d["metadata"]) for d in full_docs])[:rc.top_k]
        full_ids, full_rank, full_hits, full_false = _track_metrics(full_parents)
        top1_score = full_docs[0]["fused_score"] if full_docs else 0.0
        top1_rerank = full_docs[0]["rerank_score"] if full_docs else None

        def _ids(docs, key="wiki_id"):
            return [d.metadata.get(key, "?") for d in docs]

        full_tgt_text = next((d.page_content for d in full_parents
                              if d.metadata.get("wiki_id") == target_id), "") if target_id else ""
        missed = [f for f in expected if f not in full_tgt_text]

        eval_records.append({
            "id": qid,
            "category": test["category"],
            "query": query,
            "qtype": test.get("qtype", "hard"),
            "target_id": target_id,
            "trap_ids": trap_ids,
            "expected_count": len(expected),
            "expected": expected,
            "filter": m_filter,
            "dense_hits": dense_hits,
            "dense_rank": dense_rank,
            "dense_false": dense_false,
            "dense_ids": dense_ids,
            "dense_time": dense_time,
            "bm25_hits": bm25_hits,
            "bm25_rank": bm25_rank,
            "bm25_false": bm25_false,
            "bm25_ids": bm25_ids,
            "bm25_time": bm25_time,
            "fused_hits": fused_hits,
            "fused_rank": fused_rank,
            "fused_false": fused_false,
            "fused_ids": fused_ids,
            "fused_time": fused_time,
            "full_hits": full_hits,
            "full_rank": full_rank,
            "full_false": full_false,
            "full_ids": full_ids,
            "full_time": round(full_res["latency_ms"] + rewrite_ms, 2),
            "rewrite": rewrite,
            "rewrite_ok": (rewriter.last_ok if rewriter else None),
            "rewrite_ms": rewrite_ms,
            "rewrite_cached": (rewriter.last_cached if rewriter else None),
            "top1_score": top1_score,
            "top1_rerank": top1_rerank,
            "max_rerank": full_res.get("max_rerank_score", 0.0),
            "gate_mode": full_res.get("gate_mode", "off"),
            "gate_margin": full_res.get("gate_margin", 0.0),
            "eff_weights": full_res.get("eff_weights", [rc.rrf_weight, rc.rerank_weight]),
            "full_rejected": full_res.get("rejected", False),
            "rerank_remote": full_res.get("rerank_remote", True),
            "confusable_with": test.get("confusable_with"),
            "challenge": test["challenge_type"],
            "trace": {
                "dense_child_ids": _ids([d for d, _, _ in dense_raw], key="child_id"),
                "dense_parent_ids": _ids(dense_parents),
                "dense_scores": [round(s, 4) for _, _, s in dense_raw],
                "bm25_child_ids": _ids([d for d, _, _ in bm25_raw], key="child_id"),
                "bm25_parent_ids": _ids(bm25_parents),
                "bm25_scores": [round(s, 2) for _, _, s in bm25_raw],
                "rrf_child_ids": _ids([d for d, _ in fused], key="child_id"),
                "rrf_parent_ids": _ids(fused_parents),
                "full_parent_ids": _ids(full_parents),
                "protected_ids": [d["metadata"].get("parent_id") or d["metadata"].get("wiki_id")
                                  for d in full_docs if d.get("protected")],
                "full_fused_scores": [d["fused_score"] for d in full_docs],
                "full_rerank_scores": [d["rerank_score"] for d in full_docs],
                "scored_all": full_res.get("scored_all", []),
                "missed": missed,
            }
        })

    print("\n" + "=" * 105)
    print(f"{'题号':<8}{'题型':<12}{'目标卡':<16}{'纯Dense':<10}{'纯BM25':<10}{'RRF融合':<10}{'全链路':<10}{'时延(ms)'}")
    print("-" * 105)

    positives = [r for r in eval_records if r["target_id"]]
    negatives = [r for r in eval_records if not r["target_id"]]
    n_pos = max(len(positives), 1)
    n_neg = max(len(negatives), 1)
    total_expected = sum(r["expected_count"] for r in positives)

    def _agg(track):
        hit_n = sum(1 for r in positives if r[f"{track}_rank"])
        mrr = sum(1.0 / r[f"{track}_rank"] for r in positives if r[f"{track}_rank"]) / n_pos
        facts = sum(r[f"{track}_hits"] for r in positives)
        false_n = sum(1 for r in negatives if r[f"{track}_false"])
        return {"hit_n": hit_n, "recall": hit_n / n_pos, "mrr": mrr,
                "facts": facts, "false_n": false_n}

    stats = {t: _agg(t) for t in ("dense", "bm25", "fused", "full")}
    winners = pick_winners(stats)

    def _rank_str(r, track):
        if not r["target_id"]:
            return "误召回!" if r[f"{track}_false"] else "正确拒答"
        if track == "full" and r["full_rejected"]:
            return "✗误拒答"
        rank = r[f"{track}_rank"]
        return f"第{rank}位" if rank else "✗未召回"

    for r in eval_records:
        print(
            f"{r['id']:<8}{r['qtype']:<12}{(r['target_id'] or '—'):<16}"
            f"{_rank_str(r, 'dense'):<10}"
            f"{_rank_str(r, 'bm25'):<10}"
            f"{_rank_str(r, 'fused'):<10}"
            f"{_rank_str(r, 'full'):<10}"
            f"{r['full_time']}ms"
        )
    print("-" * 105)

    def _mk(tag):
        s = stats[tag]
        base = (f"R@3 {s['hit_n']}/{len(positives)} MRR {s['mrr']:.2f} "
                f"事实 {s['facts']}/{total_expected} 误召回 {s['false_n']}/{len(negatives)}")
        if tag not in winners:
            return base
        return f"🏆 {base}" if len(winners) == 1 else f"🏆(并列) {base}"

    verdict = "达标" if stats[winners[0]]["recall"] >= 0.8 else "未达标"
    print(f"{'汇总':<8}{'(卡级口径)':<12}{'':<16}"
          f"{_mk('dense'):<10}\n{'':<36}{_mk('bm25'):<10}\n{'':<36}{_mk('fused'):<10}\n"
          f"{'':<36}{_mk('full'):<10}\n{'':<36}判定: {verdict}")
    print("=" * 105)

    pos_max = [r["max_rerank"] for r in positives]
    neg_max = [r["max_rerank"] for r in negatives]
    if pos_max:
        print(f"原始 rerank 最高分 · 正样本: min {min(pos_max):.4f} / max {max(pos_max):.4f}"
              + (f" · 负样本: max {max(neg_max):.4f}" if neg_max else "")
              + f" · 当前 reject_threshold = {rc.reject_threshold}")
    bs = retriever.reranker.backend_stats
    if bs["calls"]:
        via = (f"KSP 网关·限定后端 {cfg.reranker_backend}" if retriever.reranker.provider == "ksp"
               else f"直连 {retriever.reranker.endpoint.split('//')[-1].split('/')[0]}")
        print(f"rerank {via}：{bs['calls']} 次打分共发起 {bs['attempts']} 次请求"
              f"（平均 {bs['attempts'] / bs['calls']:.1f} 次/打分，限流 {bs['rate_limited']} 次）")
    if rewriter:
        rw_ms = [r["rewrite_ms"] for r in eval_records if r["rewrite_cached"] is False]
        failed = [r["id"] for r in eval_records if r["rewrite_ok"] is False]
        print(f"查询改写：{len(rw_ms)} 次实际调用" + (f"，平均 {sum(rw_ms) / len(rw_ms):.0f}ms" if rw_ms else "（全部命中缓存）")
              + (f"；失败回落原查询：{', '.join(failed)}" if failed else ""))
    gates = [r.get("gate_mode", "off") for r in eval_records]
    if any(g != "off" for g in gates):
        n_hi = sum(1 for g in gates if g == "high")
        n_lo = sum(1 for g in gates if g == "low")
        print(f"置信度门控：高置信 {n_hi} 题（放权精排 {rc.gate_conf_weights}）"
              f" / 低置信 {n_lo} 题（召回托底 {rc.gate_low_weights}）"
              f"（门槛 top-1 ≥{rc.gate_min_score} 且 margin ≥{rc.gate_min_margin}）")
    degraded = [r["id"] for r in eval_records if not r["rerank_remote"]]
    if degraded:
        print(f"⚠️ 以下题目的精排降级为启发式打分，全链路结果不可与远程精排比较：{', '.join(degraded)}")

    print(f"\n[4/4] 生成并落盘评测报告文档...")
    n_q = max(len(eval_records), 1)
    avg_latency = {
        "dense": round(sum(r["dense_time"] for r in eval_records) / n_q, 1),
        "bm25": round(sum(r["bm25_time"] for r in eval_records) / n_q, 1),
        "fused": round(sum(r["fused_time"] for r in eval_records) / n_q, 1),
        "full": round(sum(r["full_time"] for r in eval_records) / n_q, 1),
    }
    report_file = out_path / f"混合检索与Rerank重排评测报告{suffix}.md"
    _generate_markdown_report(
        report_file, eval_records, stats, total_expected,
        n_pos=len(positives), n_neg=len(negatives),
        reranker_name=reranker_model, avg_latency=avg_latency,
        reject_threshold=rc.reject_threshold, rerank_granularity=rc.rerank_granularity,
        suite_label=suite_name
    )
    detail_file = out_path / f"对抗题详细召回过程{suffix}.md"
    _generate_retrieval_detail_report(detail_file, eval_records, reranker_name=reranker_model, corpus=all_chunks,
                                      rerank_granularity=rc.rerank_granularity, suite_label=suite_name)

    print(f"\n🎉 评测报告已成功落盘至：{report_file}")
    print("=" * 80)


run_day13_pipeline = run_evaluation


if __name__ == "__main__":
    import sys

    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    run_evaluation()
