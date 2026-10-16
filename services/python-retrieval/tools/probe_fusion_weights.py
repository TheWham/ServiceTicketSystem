#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_fusion_weights.py — 按秩融合权重（rrf_weight : rerank_weight）离线敏感性扫描。

背景：混合检索链路按秩融合固定 0.6(RRF) : 0.4(Rerank)。疑问是"当 Rerank 模型准确时，
压低它的权重是否会明显损失 Top-1/MRR"。本探针回答：
  - 每题只调一次检索（含远程 rerank），把候选的 rrf_rank / rerank_rank 落内存；
  - 在本地对 w_rerank = 0.0 ~ 1.0 做网格扫描，重算融合分与 Top-3，输出指标曲线；
  - 观察 Rerank 权重从 0 到 1 时，卡级 Recall@3 / MRR / Top-1 命中率 与 负样本误召回 的拐点。

局限：离线扫描不含主链路的"Top-1/2 双路共振保护"（该保护在 hybrid_rerank_search 内部
落地，与权重正交），故扫描值略低估 RRF 侧的召回下限；结论看趋势与拐点即可。

用法：
  python tools/probe_fusion_weights.py                 # 默认扫 Day13 HC/NEG 题集
  python tools/probe_fusion_weights.py --dataset day14 # 扫 Day14 黄金集（含冲突/对抗题）
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

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
from rag_pipeline.evaluation.suite import HARD_BENCHMARK_SUITE
import run_day14_pipeline as d14

WEIGHTS = [round(i * 0.1, 1) for i in range(11)]  # 0.0 ~ 1.0


def _parent_of(meta: Dict[str, Any]) -> str:
    return meta.get("parent_id") or meta.get("wiki_id") or meta.get("child_id") or "?"


def load_queries(dataset: str) -> List[Dict[str, Any]]:
    """统一成 [{id, query, target, traps, kind}]，kind ∈ pos/neg。"""
    if dataset == "day13":
        out = []
        for q in HARD_BENCHMARK_SUITE:
            is_neg = q.get("qtype") == "negative"
            out.append({"id": q["id"], "query": q["query"],
                        "target": [] if is_neg else [q.get("target_id")],
                        "traps": list(q.get("trap_ids") or []),
                        "kind": "neg" if is_neg else "pos"})
        return out
    golden = json.loads((REPO_ROOT / "evals" / "golden_dataset_v1.0.json").read_text(encoding="utf-8"))
    out = []
    for q in golden:
        if q.get("is_adversarial"):
            continue  # 拒答题与融合权重无关（由 rerank 绝对分阈值截断）
        targets = [d14._parent_id_of(c) for c in q.get("reference_chunk_ids", [])]
        out.append({"id": q["id"], "query": q["query"], "target": targets,
                    "traps": [], "kind": "pos"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="day13", choices=["day13", "day14"])
    args = ap.parse_args()

    cfg = load_config()
    rc = cfg.retrieval
    queries = load_queries(args.dataset)

    print("=" * 96)
    print(f"⚙️  融合权重敏感性扫描（{args.dataset} 题集，{len(queries)} 题，产线配置 fuse_k={rc.fuse_k}）")
    print(f"    产线默认：rrf_weight={rc.rrf_weight} / rerank_weight={rc.rerank_weight}")
    print("=" * 96)

    # ---- 每题调一次检索，落候选名次（rerank 用改写查询，与产线链路一致）----
    # 候选落盘缓存：同一题集/配置指纹下重跑零 API 成本（权重扫描纯离线）
    cache_dir = REPO_ROOT / "artifacts" / "evaluation" / ".probe_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"fusion_cands_{args.dataset}.json"
    cache_key = f"{args.dataset}|{len(queries)}"
    cached = None
    if cache_file.exists():
        try:
            blob = json.loads(cache_file.read_text(encoding="utf-8"))
            if blob.get("key") == cache_key:
                cached = blob["per_query"]
                print(f"  ♻️ 命中候选缓存 {cache_file.name}（跳过全部 API 调用）")
        except Exception:
            cached = None

    if cached:
        per_query = cached
    else:
        # 仅在需要真实检索时才装配（缓存命中时零 API、零 embedding 自检）
        corpus = d14.load_corpus_with_deterministic_ids(REPO_ROOT / "artifacts/output/wiki", cfg)
        embed = KspEmbeddingProvider(cache_dir=str(REPO_ROOT / cfg.embedding_cache_dir))
        vdb = Chroma(persist_directory=str(REPO_ROOT / "artifacts/indexing/chroma_wiki_structured"),
                     embedding_function=embed, collection_name=cfg.store_collection)
        retriever = IndustrialHybridRetriever(vector_db=vdb, corpus_docs=corpus,
                                              reranker_model_name=cfg.reranker_model,
                                              default_exclude=rc.default_exclude)
        rewriter = QueryRewriter(model=rc.rewrite_model,
                                 cache_dir=str(REPO_ROOT / "artifacts/evaluation/.llm_cache/rewrite")) \
            if rc.query_rewrite else None

        per_query = []
        for i, q in enumerate(queries, 1):
            rewrite = rewriter.rewrite(q["query"]) if rewriter else None
            res = retriever.hybrid_rerank_search(
                query=q["query"], final_top_k=rc.top_k, rrf_k=rc.rrf_k, rough_top_k=rc.rough_top_k,
                fuse_k=rc.fuse_k, rrf_weight=rc.rrf_weight, rerank_weight=rc.rerank_weight,
                reject_threshold=None, heuristic_reject_threshold=None,  # 扫描关注排序质量，关闭物理拒答（含降级路径）
                rerank_granularity=rc.rerank_granularity, rewrite_query=rewrite)
            cands = res.get("scored_all") or []
            per_query.append({"q": q, "cands": cands})
            print(f"  [{i:>2}/{len(queries)}] {q['id']:<9} 候选 {len(cands):>2}  "
                  f"（rerank {'降级' if res.get('max_rerank_score', 0) == 0 else '正常'}）")
        cache_file.write_text(json.dumps({"key": cache_key, "per_query": per_query},
                                         ensure_ascii=False), encoding="utf-8")
        print(f"  💾 候选已缓存 → {cache_file.name}")

    # ---- 离线网格扫描 ----
    def rank_target(rec: Dict[str, Any], w_rerank: float) -> Dict[str, Any]:
        """返回该题在权重 w_rerank 下：去重父块全序 + 各目标卡名次（1 起，未召回=None）。"""
        w_rrf = round(1.0 - w_rerank, 1)
        k = rc.fuse_k
        scored = []
        for c in rec["cands"]:
            fused = (w_rrf / (k + c["rrf_rank"])) + (w_rerank / (k + c["rerank_rank"]))
            scored.append((fused, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        parents: List[str] = []
        for _, c in scored:
            p = _parent_of(c["metadata"])
            if p not in parents:
                parents.append(p)
        tgt = rec["q"]["target"]
        targets = set(tgt) if isinstance(tgt, (list, set)) else {tgt}
        rank = next((i for i, p in enumerate(parents, 1) if p in targets), None)
        return {"order": parents, "rank": rank}

    def eval_at(w_rerank: float, top_k: int = 3) -> Dict[str, Any]:
        n_pos = n_neg = 0
        hit1 = hitk = 0
        rr3 = rr_full = 0.0
        false_recall = 0
        worst = []
        for rec in per_query:
            q = rec["q"]
            r = rank_target(rec, w_rerank)
            top = r["order"][:top_k]
            if q["kind"] == "neg":
                n_neg += 1
                if set(q["traps"]) & set(top):
                    false_recall += 1
                continue
            n_pos += 1
            rank = r["rank"]
            if rank == 1:
                hit1 += 1
            if rank and rank <= top_k:
                hitk += 1
                rr3 += 1.0 / rank
            if rank:
                rr_full += 1.0 / rank
                if rank > 1:
                    worst.append((q["id"], rank))
            else:
                worst.append((q["id"], 99))
        worst.sort(key=lambda x: -x[1])
        return {"recall@3": hitk / n_pos if n_pos else 0.0,
                "top1": hit1 / n_pos if n_pos else 0.0,
                "mrr3": rr3 / n_pos if n_pos else 0.0,
                "mrr_full": rr_full / n_pos if n_pos else 0.0,
                "neg_false": f"{false_recall}/{n_neg}" if n_neg else "—",
                "worst": worst[:3]}

    print()
    print("-" * 104)
    print(f"{'w_rerank':<10}{'w_rrf':<8}{'Recall@3':<12}{'Top-1':<10}{'MRR@3':<10}{'MRR全序':<10}"
          f"{'负样本误召回':<14}{'最差题(名次)'}")
    print("-" * 104)
    rows = {}
    for w in WEIGHTS:
        m = eval_at(w)
        rows[w] = m
        mark = " ←产线" if abs(w - rc.rerank_weight) < 1e-6 else ""
        worst_txt = "、".join(f"{i}#{('未召回' if r == 99 else r)}" for i, r in m["worst"])
        print(f"{w:<10.1f}{round(1.0 - w, 1):<8.1f}{m['recall@3']:<12.1%}{m['top1']:<10.1%}"
              f"{m['mrr3']:<10.3f}{m['mrr_full']:<10.3f}{m['neg_false']:<14}{worst_txt}{mark}")

    best_mrr = max(WEIGHTS, key=lambda w: (rows[w]["mrr_full"], rows[w]["recall@3"]))
    best_rec = max(WEIGHTS, key=lambda w: (rows[w]["recall@3"], rows[w]["mrr_full"]))
    print("-" * 104)
    print(f"→ 全序 MRR 最优：w_rerank={best_mrr:.1f} (MRR {rows[best_mrr]['mrr_full']:.3f})；"
          f"Recall@3 最优：w_rerank={best_rec:.1f} ({rows[best_rec]['recall@3']:.1%})")
    d = rc.rerank_weight
    print(f"→ 产线 w_rerank={d:.1f}：Recall@3 {rows[d]['recall@3']:.1%} / 全序MRR {rows[d]['mrr_full']:.3f}；"
          f"相对全序最优差 {rows[d]['mrr_full'] - rows[best_mrr]['mrr_full']:+.3f}")

    # ---- 逐题名次漂移：三档权重对比，暴露权重真正影响哪些题 ----
    print()
    print("-" * 104)
    print("逐题名次对比（w_rerank = 0.0 纯RRF / 0.4 产线 / 1.0 纯Rerank；仅列有差异的题）")
    print("-" * 104)
    for rec in per_query:
        q = rec["q"]
        r0, r4, r1 = (rank_target(rec, w)["rank"] for w in (0.0, rc.rerank_weight, 1.0))
        if r0 != r4 or r4 != r1:
            f = lambda x: "未召回" if x is None else f"#{x}"
            print(f"  {q['id']:<9} [{q['kind']}]  纯RRF {f(r0):<8} → 产线 {f(r4):<8} → 纯Rerank {f(r1)}")

    # ---- 分歧率：RRF 序与 Rerank 序的 Top-3 父块是否一致（权重是否真正起作用的前提）----
    print()
    print("-" * 104)
    print("RRF 序 vs Rerank 序 分歧诊断（目标卡名次 & Top-3 父块集合）")
    print("-" * 104)
    diff_top1 = diff_top3 = 0
    for rec in per_query:
        o0 = rank_target(rec, 0.0)["order"][:3]
        o1 = rank_target(rec, 1.0)["order"][:3]
        r0 = rank_target(rec, 0.0)["rank"]
        r1 = rank_target(rec, 1.0)["rank"]
        if o0[0] != o1[0]:
            diff_top1 += 1
        if set(o0) != set(o1):
            diff_top3 += 1
            print(f"  {rec['q']['id']:<9} RRF Top-3 {o0}  ≠  Rerank Top-3 {o1}"
                  f"  目标名次 {r0} → {r1}")
    print(f"  → Top-1 父块不一致 {diff_top1}/{len(per_query)} 题；Top-3 集合不一致 {diff_top3}/{len(per_query)} 题")
    if diff_top3 == 0:
        print("  ⚠️ 两序完全一致：当前语料规模下 rerank 与 RRF 对 Top-3 判断无分歧，"
              "权重取值对指标不可分辨（饱和），0.6/0.4 属防御性配置而非性能驱动参数")

    # ---- 翻盘能力：产线权重下 rerank 需要多大名次优势才能逆转 RRF 的第 1 名 ----
    print()
    print("-" * 104)
    print(f"翻盘能力分析（产线 w_rrf={rc.rrf_weight} / w_rerank={rc.rerank_weight}, fuse_k={rc.fuse_k}）")
    print("-" * 104)
    w_r, w_k, k = rc.rrf_weight, rc.rerank_weight, rc.fuse_k

    def wins(rank_a_rrf, rank_a_rr_, rank_b_rrf, rank_b_rr):
        a = w_r / (k + rank_a_rrf) + w_k / (k + rank_a_rr_)
        b = w_r / (k + rank_b_rrf) + w_k / (k + rank_b_rr)
        return b > a, a, b

    print("  场景：卡A(RRF第1, Rerank第m) vs 卡B(RRF第n, Rerank第1)——rerank 认定 B 才是真答案")
    print(f"  {'RRF差 n':<10}{'Rerank差 m':<12}{'B 能否翻盘':<12}{'A融合分':<12}{'B融合分'}")
    for n in (2, 3, 5, 8):
        for m in (3, 5, 8, 12):
            ok, a, b = wins(1, m, n, 1)
            print(f"  {n:<10}{m:<12}{'✅ 翻盘' if ok else '❌ 压不住':<12}{a:<12.5f}{b:.5f}")
    print()
    print(f"  → 对称对调（A: RRF1/Rerank{m}, B: RRF{m}/Rerank1）永远翻不了盘："
          f"w_rerank({w_k}) < w_rrf({w_r}) 时 RRF 第1名稳赢；")
    print("    但只要 rerank 的名次优势明显大于 RRF 的名次劣势（非对称），0.4 权重仍可逆转——"
          "上表 n=2,m=8 即为一例。")


if __name__ == "__main__":
    main()
