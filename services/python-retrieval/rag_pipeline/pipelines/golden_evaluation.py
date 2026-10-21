"""黄金问题集评测 CLI 装配入口。

    python -m rag_pipeline.pipelines.golden_evaluation

装配主链路混合重排检索器（复用 rag_pipeline 配置中心与持久化向量库，manifest 指纹校验），
交给 `rag_pipeline.evaluation.golden.GoldenSetEvaluator` 跑 evals/golden_dataset_v1.0.json，
并落盘量化体检大盘报告。
"""

import argparse
import json
import sys
from pathlib import Path

import warnings
warnings.filterwarnings("ignore")

try:
    from langchain_community.vectorstores import Chroma
except ImportError:
    Chroma = None

from ..chunking.corpus import load_corpus_with_deterministic_ids
from ..chunking.fingerprint import compute_wiki_fingerprint
from ..config import REPO_ROOT, config_fingerprint, load_config
from ..embedding import KspEmbeddingProvider
from ..evaluation.golden import GoldenSetEvaluator
from ..retrieval.hybrid import IndustrialHybridRetriever
from ..retrieval.query_rewriter import QueryRewriter


def run_golden_evaluation():
    parser = argparse.ArgumentParser(description="黄金问题集 RAG 评测基准流水线")
    parser.add_argument("--wiki-dir", default="artifacts/output/wiki", help="Wiki 卡片目录")
    parser.add_argument("--chroma-dir", default="artifacts/indexing/chroma_wiki_structured", help="持久化向量库目录")
    parser.add_argument("--golden-dataset", default="evals/golden_dataset_v1.0.json", help="黄金问题集路径")
    parser.add_argument("--output-dir", default="artifacts/evaluation", help="评测产物输出目录")
    parser.add_argument("--top-k", type=int, default=None, help="评测 Top-K（默认取 pipeline.yaml retrieval.top_k）")
    parser.add_argument("--adversarial-threshold", type=float, default=None,
                        help="拒答置信截断阈值（默认自动标定=正样本 top-1 rerank 分最小值）")
    args = parser.parse_args()

    print("=" * 80)
    print("🎯 黄金问题集 RAG 检索层量化评估基准流水线")
    print("=" * 80)

    cfg = load_config()
    top_k = args.top_k or cfg.retrieval.top_k
    wiki_path = REPO_ROOT / args.wiki_dir
    chroma_path = REPO_ROOT / args.chroma_dir
    golden_path = REPO_ROOT / args.golden_dataset
    output_path = REPO_ROOT / args.output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 载入语料并绑定确定性 chunk_id（与黄金集 reference_chunk_ids 对齐）
    print("\n[1/3] 提取 Wiki 知识切片语料并绑定确定性溯源 Chunk ID...")
    corpus_docs = load_corpus_with_deterministic_ids(wiki_path, cfg)
    print(f"       -> 成功提取并装配切片语料：{len(corpus_docs)} 个标准 Chunks")

    # 2. 装配 IndustrialHybridRetriever（优先加载持久化库，manifest 指纹校验）
    print("\n[2/3] 装配工业级双路混合检索与重排核心中枢...")
    embed_provider = KspEmbeddingProvider(cache_dir=str(REPO_ROOT / cfg.embedding_cache_dir))
    vector_db = None
    stale_reason = None
    manifest_file = chroma_path / "manifest.json"
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
            try:
                vector_db = Chroma(persist_directory=str(chroma_path),
                                   embedding_function=embed_provider,
                                   collection_name=cfg.store_collection)
                print(f"       -> 成功加载持久化向量数据库：{chroma_path.name}")
            except Exception as e:
                stale_reason = f"加载异常({e})"
    if vector_db is None and Chroma is not None:
        if stale_reason:
            print(f"       ⚠️ 持久化库不可用（{stale_reason}），内存重建索引...")
        vector_db = Chroma.from_documents(documents=corpus_docs, embedding=embed_provider,
                                          collection_name="wiki_structured_golden_eval")

    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=corpus_docs,
        reranker_model_name=cfg.reranker_model,
        default_exclude=cfg.retrieval.default_exclude,
    )

    # 查询改写器：与主链路评测同一装配（yaml query_rewrite 开关，缓存落评测产物目录）
    rewriter = QueryRewriter(
        model=cfg.retrieval.rewrite_model,
        cache_dir=str(output_path / ".llm_cache" / "rewrite"),
    ) if cfg.retrieval.query_rewrite else None
    if rewriter:
        print(f"       -> 查询改写已启用：{rewriter.model}（磁盘缓存 evaluation/.llm_cache/rewrite）")

    # 3. 运行评测大盘
    print(f"\n[3/3] 启动 GoldenSetEvaluator 对《{golden_path.name}》进行量化评估...")
    evaluator = GoldenSetEvaluator(retriever=retriever, golden_dataset_path=str(golden_path),
                                   rc=cfg.retrieval, rewriter=rewriter)
    summary = evaluator.run_evaluation(top_k=top_k, adversarial_threshold=args.adversarial_threshold)

    # 门控档位分布（生产级可观测性：说明融合权重是固定还是按置信度切换）
    gate_modes = [d.get("gate_mode", "off") for d in summary["details"]]
    if any(m != "off" for m in gate_modes):
        print(f"置信度门控：高置信 {gate_modes.count('high')} 题（放权精排 "
              f"{cfg.retrieval.gate_conf_weights}）/ 低置信 {gate_modes.count('low')} 题（召回托底 "
              f"{cfg.retrieval.gate_low_weights}）（门槛 top-1 ≥{cfg.retrieval.gate_min_score} "
              f"且 margin ≥{cfg.retrieval.gate_min_margin}）")

    # 4. 报告落盘
    report_file = output_path / "黄金问题集RAG评测基准报告.md"
    evaluator.generate_markdown_report(report_file, summary, top_k=top_k)
    print(f"\n🎉 评测报告已成功落盘至：{report_file}")
    print("=" * 80)


if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    run_golden_evaluation()
