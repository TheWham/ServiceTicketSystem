#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day13 薄入口（向后兼容壳）。

实现已迁移至 rag_pipeline 包：
  - 主流水线    -> rag_pipeline.pipelines.day13
  - 检索器      -> rag_pipeline.retrieval.*
  - 评测与报告  -> rag_pipeline.evaluation.*
本文件仅做转发与 API 再导出，adversarial_benchmark / trace_retrieval
等工具脚本的旧 import（from run_day13_pipeline import ...）继续可用。
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
from rag_pipeline.chunking.structure_aware import WikiStructureAwareChunker
from rag_pipeline.chunking.parent_child import ParentChildChunker, expand_to_parents
from rag_pipeline.chunking.fingerprint import compute_wiki_fingerprint
from rag_pipeline.retrieval.tokenizer import ChineseTokenizer, PurePythonBM25
from rag_pipeline.retrieval.reranker import KspReranker
from rag_pipeline.retrieval.hybrid import IndustrialHybridRetriever
from rag_pipeline.evaluation.suite import HARD_BENCHMARK_SUITE
from rag_pipeline.pipelines.evaluation import run_evaluation, run_day13_pipeline

__all__ = [
    "load_ksp_config", "KspEmbeddingProvider",
    "WikiStructureAwareChunker", "ParentChildChunker", "expand_to_parents",
    "compute_wiki_fingerprint",
    "ChineseTokenizer", "PurePythonBM25", "KspReranker", "IndustrialHybridRetriever",
    "HARD_BENCHMARK_SUITE", "run_evaluation", "run_day13_pipeline",
]


if __name__ == "__main__":
    run_evaluation()
