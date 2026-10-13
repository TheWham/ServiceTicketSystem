#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day12 薄入口（向后兼容壳）。

实现已迁移至 rag_pipeline 包：
  - 主流水线    -> rag_pipeline.pipelines.day12
  - 切块器      -> rag_pipeline.chunking.*
  - 嵌入/配置   -> rag_pipeline.embedding / rag_pipeline.config
本文件仅做转发与 API 再导出，adversarial_benchmark / dump_chunks /
ingest_vector_store / inspect_chroma / trace_retrieval 等工具脚本的
旧 import（from run_day12_pipeline import ...）继续可用。
"""

import sys

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")

# ---- 向后兼容再导出 ----
from rag_pipeline.embedding import load_ksp_config, KspEmbeddingProvider
from rag_pipeline.chunking.structure_aware import WikiStructureAwareChunker, NaiveFixedChunker
from rag_pipeline.chunking.parent_child import ParentChildChunker, expand_to_parents
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.store import VectorStoreManager
from rag_pipeline.evaluation.suite import BENCHMARK_QUERIES
from rag_pipeline.pipelines.indexing import run_indexing, run_day12_pipeline, _generate_markdown_report

__all__ = [
    "load_ksp_config", "KspEmbeddingProvider",
    "WikiStructureAwareChunker", "NaiveFixedChunker",
    "ParentChildChunker", "expand_to_parents", "compute_wiki_fingerprint",
    "VectorStoreManager", "BENCHMARK_QUERIES",
    "run_day12_pipeline", "_generate_markdown_report",
]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Day 12 结构感知切块与向量库调优流水线")
    parser.add_argument("--wiki-dir", default="output/wiki", help="Day 11 Wiki 卡片输入目录")
    parser.add_argument("--raw-dir", default="day11/demos", help="原始未治理文档输入目录(可选,不存在则用wiki做朴素对照)")
    parser.add_argument("--output-dir", default="day12_output", help="Day 12 产物输出目录")
    parser.add_argument("--model", default="", help="Embedding 模型名(默认取 KSP_EMBED_MODEL 或 qwen3-embedding-8b)")
    args = parser.parse_args()

    run_indexing(
        wiki_kb_dir=args.wiki_dir,
        raw_docs_dir=args.raw_dir,
        output_dir=args.output_dir,
        embedding_model=args.model
    )
