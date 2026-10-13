"""检索评测主流水线（原 Day13）：四轨对比评测 + 报告落盘。"""

import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

try:
    from langchain_community.vectorstores import Chroma
    import chromadb
except ImportError:
    Chroma = None
    chromadb = None

from ..config import load_config, config_fingerprint, build_chunker
from ..embedding import load_ksp_config, KspEmbeddingProvider
from ..chunking.structure_aware import WikiStructureAwareChunker
from ..chunking.parent_child import ParentChildChunker, expand_to_parents
from ..chunking.fingerprint import compute_wiki_fingerprint
from ..retrieval.hybrid import IndustrialHybridRetriever
from ..evaluation.suite import HARD_BENCHMARK_SUITE
from ..evaluation.report import _generate_markdown_report, _generate_retrieval_detail_report


def run_evaluation():
    """Day 13 主流水线：载入语料/向量库 -> 装配混合检索器 -> 四轨评测 -> 报告。

    四轨对比（同一道题跑四条链路，量化各阶段增益）：
      A 纯 Dense 向量检索
      B 纯 BM25 关键词检索
      C Dense + BM25 + RRF 融合（无精排）
      D 全链路：元数据过滤 + 双路召回 + RRF + Rerank 精排 + 按秩融合兜底
    """
    parser = argparse.ArgumentParser(description="Day 13 混合检索机制与 Rerank 重排优化流水线")
    parser.add_argument("--wiki-dir", default="output/wiki", help="Day 11 Wiki 卡片目录")
    parser.add_argument("--chroma-dir", default="day12_output/chroma_wiki_structured", help="Day 12 结构化向量库目录")
    parser.add_argument("--output-dir", default="day13_output", help="Day 13 产物输出目录")
    parser.add_argument("--reranker", default="", help="重排模型名称(默认取 KSP_RERANK_MODEL 或 qwen3-reranker-8b)")
    args = parser.parse_args()

    cfg = load_config()
    # 重排模型名：命令行 > 环境变量/.env > pipeline.yaml > 内置默认
    reranker_model = args.reranker or load_ksp_config().get("rerank_model") or cfg.reranker_model

    print("=" * 80)
    print("🚀 Day 13 Wiki 术语归一化、双路混合检索与 Rerank 深度重排优化实战流水线")
    print("=" * 80)

    # 项目根 = 本文件上两级（rag_pipeline/pipelines/ -> 仓库根）
    project_root = Path(__file__).resolve().parents[2]
    wiki_path = project_root / args.wiki_dir
    chroma_path = project_root / args.chroma_dir
    out_path = project_root / args.output_dir
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. 自动读取 Day 11 的 Wiki 知识卡片并生成结构化切片作为倒排语料
    print(f"\n[1/4] 载入知识基座切片语料与 Chroma 向量数据库...")

    # 切块器经配置中心工厂实例化——与 Day 12 建库走同一路径，
    # 改 configs/pipeline.yaml 后两侧语料粒度自动保持一致。
    chunker, use_parent_child = build_chunker(cfg)

    if KspEmbeddingProvider is not None:
        # 复用与 Day 12 相同的嵌入模型与磁盘缓存，保证维度一致(4096)
        embed_provider = KspEmbeddingProvider(cache_dir=str(project_root / cfg.embedding_cache_dir))
        print(f"       -> Embedding 引擎: 【{embed_provider.engine_type}】")
    else:
        embed_provider = None
        print("       ⚠️ 未复用到 KspEmbeddingProvider，Dense 通道可能不可用")

    # _index.md 是目录导航页非知识正文，排除避免污染检索
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

    # 语料一致性校验：比对 Day 12 落盘的 manifest 指纹与当前 Wiki 卡片/切块参数。
    # 不校验的后果：04 重跑或卡片改动后，Chroma 里是旧文本 embedding、BM25 是运行时
    # 新切块，两路召回的不是同一批 chunk，RRF 按 page_content 去重直接失效。
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

    # 载入或构建向量数据库
    vector_db = None
    if Chroma is not None and chroma_path.exists() and stale_reason is None:
        try:
            vector_db = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=embed_provider,
                collection_name="wiki_structured_kb"
            )
            print(f"       -> 成功加载 Day 12 持久化向量数据库：{chroma_path.name}")
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

    # 2. 装配工业级双路混合检索器
    # default_exclude：把对抗压测验证过的"元数据物理屏蔽废止卡"固化进主链路
    print(f"\n[2/4] 初始化装配 IndustrialHybridRetriever 混合检索与重排核心...")
    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=all_chunks,
        reranker_model_name=reranker_model,
        default_exclude=cfg.retrieval.default_exclude
    )

    # 3. 执行 4 轨架构对比大比武评测 (Benchmark)
    print(f"\n[3/4] 执行 12 组对抗评测：7 硬匹配 + 3 同义改写 + 2 库外负样本（四轨对比大比武）...")
    rc = cfg.retrieval
    eval_records = []

    for test in HARD_BENCHMARK_SUITE:
        qid = test["id"]
        query = test["query"]
        expected = test["expected_facts"]
        m_filter = test["filter"]
        target_id = test.get("target_id")
        trap_ids = test.get("trap_ids", [])

        def _track_metrics(parents):
            """卡级打分：返回 (回溯父块 id 序列, 目标卡名次, 严格事实命中数, 是否误召回陷阱卡)。

            名次以 expand_to_parents 去重后的父块顺序为准（1=Top-1）；目标卡未召回名次为 None。
            事实命中只在"检索到的目标卡正文"内计数——目标卡没被召回，事实一律记 0，
            杜绝旧口径下高频通用词在错误卡片上误命中造成的分数虚高。
            """
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

        # 轨 1: 纯 Dense 向量检索（子块匹配，Top-3），命中后回溯父块算卡级名次
        t0 = time.time()
        dense_raw = retriever.dense_search(query, top_k=rc.top_k, metadata_filter=m_filter)
        dense_time = round((time.time() - t0) * 1000, 1)
        dense_parents = expand_to_parents([d for d, _, _ in dense_raw]) if expand_to_parents else [d for d, _, _ in dense_raw]
        dense_ids, dense_rank, dense_hits, dense_false = _track_metrics(dense_parents)

        # 轨 2: 纯 BM25 关键词检索（子块匹配，Top-3），命中后回溯父块
        t0 = time.time()
        bm25_raw = retriever.bm25_search(query, top_k=rc.top_k, metadata_filter=m_filter)
        bm25_time = round((time.time() - t0) * 1000, 1)
        bm25_parents = expand_to_parents([d for d, _, _ in bm25_raw]) if expand_to_parents else [d for d, _, _ in bm25_raw]
        bm25_ids, bm25_rank, bm25_hits, bm25_false = _track_metrics(bm25_parents)

        # 轨 3: Dense + BM25 双路召回 + RRF 融合（无精排，Top-3）
        # 与轨 4 的唯一区别是：不做 Rerank 精排与按秩融合，用于隔离出精排环节的真实增益
        t0 = time.time()
        fused = retriever.rrf_fusion(bm25_raw, dense_raw, rrf_k=rc.rrf_k, candidate_limit=rc.top_k)
        fusion_time = round((time.time() - t0) * 1000, 1)
        # 轨 3 端到端延迟 = 双路召回(dense+bm25) + RRF 融合，与轨 1/2 的口径对齐
        fused_time = round(dense_time + bm25_time + fusion_time, 1)
        fused_parents = expand_to_parents([d for d, _ in fused]) if expand_to_parents else [d for d, _ in fused]
        fused_ids, fused_rank, fused_hits, fused_false = _track_metrics(fused_parents)

        # 轨 4: 顶级工业级全链路（元数据过滤 + 双路召回 + RRF + Rerank 精排 + 按秩融合兜底）
        full_res = retriever.hybrid_rerank_search(
            query=query,
            final_top_k=rc.top_k,
            rrf_k=rc.rrf_k,
            rough_top_k=rc.rough_top_k,
            fuse_k=rc.fuse_k,
            rrf_weight=rc.rrf_weight,
            rerank_weight=rc.rerank_weight,
            metadata_filter=m_filter
        )
        full_docs = full_res["final_results"]
        full_parents = expand_to_parents(full_docs) if expand_to_parents else [Document(page_content=d["content"], metadata=d["metadata"]) for d in full_docs]
        full_ids, full_rank, full_hits, full_false = _track_metrics(full_parents)
        # top1_score 取融合分（按秩加权），用于评估精排 Top-1 的相关度置信度
        top1_score = full_docs[0]["fused_score"] if full_docs else 0.0

        def _ids(docs, key="wiki_id"):
            return [d.metadata.get(key, "?") for d in docs]

        # 严格漏项：以全链路检索到的目标卡正文为基准（目标卡未召回则全部记漏）
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
            "full_time": full_res["latency_ms"],
            "top1_score": top1_score,
            "challenge": test["challenge_type"],
            # ===== 详细召回轨迹（供"7组详细召回过程"报告使用）=====
            "trace": {
                # 子块列用 child_id（能看出命中的是第几个子块），父块列用卡片 id
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
                "scored_all": full_res.get("scored_all", []),
                "missed": missed,
            }
        })

    # 控制台打印对比表（卡级名次口径：数字=目标卡在 Top-3 的名次，✗=未召回）
    print("\n" + "=" * 105)
    print(f"{'题号':<8}{'题型':<12}{'目标卡':<16}{'纯Dense':<10}{'纯BM25':<10}{'RRF融合':<10}{'全链路':<10}{'时延(ms)'}")
    print("-" * 105)

    positives = [r for r in eval_records if r["target_id"]]
    negatives = [r for r in eval_records if not r["target_id"]]
    n_pos = max(len(positives), 1)
    n_neg = max(len(negatives), 1)
    total_expected = sum(r["expected_count"] for r in positives)

    def _agg(track):
        """汇总单轨四项核心指标：卡级 Recall@3、MRR、严格事实命中数、负样本误召回数。"""
        hit_n = sum(1 for r in positives if r[f"{track}_rank"])
        mrr = sum(1.0 / r[f"{track}_rank"] for r in positives if r[f"{track}_rank"]) / n_pos
        facts = sum(r[f"{track}_hits"] for r in positives)
        false_n = sum(1 for r in negatives if r[f"{track}_false"])
        return {"hit_n": hit_n, "recall": hit_n / n_pos, "mrr": mrr,
                "facts": facts, "false_n": false_n}

    stats = {t: _agg(t) for t in ("dense", "bm25", "fused", "full")}

    # 数据驱动：真实算出哪条链路最优才标 🏆（Recall@3 优先，MRR 次之，事实数兜底）
    winner = max(stats, key=lambda t: (stats[t]["recall"], stats[t]["mrr"], stats[t]["facts"]))

    def _rank_str(r, track):
        if not r["target_id"]:
            return "误召回!" if r[f"{track}_false"] else "正确拒答"
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
        return f"🏆 {base}" if tag == winner else base

    verdict = "达标" if stats[winner]["recall"] >= 0.8 else "未达标"
    print(f"{'汇总':<8}{'(卡级口径)':<12}{'':<16}"
          f"{_mk('dense'):<10}\n{'':<36}{_mk('bm25'):<10}\n{'':<36}{_mk('fused'):<10}\n"
          f"{'':<36}{_mk('full'):<10}\n{'':<36}判定: {verdict}")
    print("=" * 105)

    # 4. 生成评测实验报告 Markdown 落盘
    print(f"\n[4/4] 生成并落盘评测报告文档...")
    # 真实平均端到端延迟：从每题实测值求均值（不再用模板写死的假数字）
    n_q = max(len(eval_records), 1)
    avg_latency = {
        "dense": round(sum(r["dense_time"] for r in eval_records) / n_q, 1),
        "bm25": round(sum(r["bm25_time"] for r in eval_records) / n_q, 1),
        "fused": round(sum(r["fused_time"] for r in eval_records) / n_q, 1),
        "full": round(sum(r["full_time"] for r in eval_records) / n_q, 1),
    }
    report_file = out_path / "Day13_混合检索与Rerank重排评测报告.md"
    _generate_markdown_report(
        report_file, eval_records, stats, total_expected,
        n_pos=len(positives), n_neg=len(negatives),
        reranker_name=reranker_model, avg_latency=avg_latency
    )
    # 同时生成"对抗题详细召回过程"报告（父子切片 Small-to-Big 全程轨迹）
    detail_file = out_path / "Day13_对抗题详细召回过程.md"
    _generate_retrieval_detail_report(detail_file, eval_records, reranker_name=reranker_model, corpus=all_chunks)

    print(f"\n🎉 评测报告已成功落盘至：{report_file}")
    print("=" * 80)


# 向后兼容别名：旧入口与工具脚本仍可用 run_day13_pipeline
run_day13_pipeline = run_evaluation
