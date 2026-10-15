#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
ingest_vector_store.py — 基于 Wiki 结构与元数据注入的向量库批量入库工程
================================================================================
适配企业 IT 知识库（清洗流水线产出的 35 张 Wiki 卡片 output/wiki/ITKB-*.md）：
  1. Embedding 模型替换为 KSP OpenAI 兼容端点 qwen3-embedding-8b（4096 维）
  2. 批量读取整个 Wiki 卡片目录（而非单张测试卡片）
  3. Frontmatter 自动解析 → Markdown 标题树切分 → 递归微切 → 元数据深度注入
  4. 持久化到 Chroma，断点续跑借助 .emb_cache 磁盘缓存零重复调用
  5. 入库后即用一条真实 IT 业务问题验证元数据检索
================================================================================
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List

# 脚本位于 tools/，向上定位仓库根并加入 sys.path，便于 import rag_pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from rag_pipeline.config import WIKI_DIR, INDEXING_OUTPUT
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.chunking.structure_aware import WikiStructureAwareChunker


class WikiKnowledgeIngestionPipeline:
    """读取带 YAML Frontmatter 的 Wiki 卡片，注入元数据后批量灌入 Chroma。

    与 rag_pipeline.pipelines.indexing（建库主流水线）的区别：本脚本是"纯入库工具"，只负责
    切块 + 向量化 + 落盘到独立 chroma_db，不跑评测对照，适合单独验证入库链路。
    """

    def __init__(
        self,
        persist_directory: str = str(INDEXING_OUTPUT / "chroma_db"),
        embedding_provider: KspEmbeddingProvider = None,
        chunk_size: int = 550,
        chunk_overlap: int = 80,
    ):
        self.persist_directory = persist_directory

        # 1. 初始化 Embedding 模型（KSP qwen3-embedding-8b，4096 维，余弦归一化）
        #    embedding 缓存放在产物目录下，重复入库时命中缓存、零重复 API 调用
        print("⚡ 正在加载 Embedding 模型...")
        self.embeddings = embedding_provider or KspEmbeddingProvider(
            cache_dir=str(Path(persist_directory).parent / ".emb_cache")
        )
        print(f"   -> Embedding 引擎: 【{self.embeddings.engine_type}】")

        # 2+3. 复用自适应粒度切块器（短卡片整卡原子化，长文档多级切分）
        self.chunker = WikiStructureAwareChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def process_and_ingest_dir(self, wiki_dir: str):
        """批量读取目录下所有 Wiki 卡片并注入向量数据库。

        返回可检索的 Chroma 句柄。_index.md 是目录导航页，排除以避免污染检索。
        """
        wiki_path = Path(wiki_dir)
        files = sorted(wiki_path.glob("*.md"))
        files = [f for f in files if f.name != "_index.md"]  # 排除目录导航页
        if not files:
            raise FileNotFoundError(f"❌ 未在 {wiki_path} 找到任何 .md Wiki 卡片")

        print(f"📖 正在解析企业 Wiki 卡片目录：{wiki_path}（共 {len(files)} 张）...")
        final_docs: List[Document] = []
        for fp in files:
            chunks = self.chunker.split_wiki_document(str(fp))
            final_docs.extend(chunks)
            print(f"   - {fp.name} -> {len(chunks)} 个结构化切片")

        print(f"✅ 成功拆解为 {len(final_docs)} 个高纯度结构化 Chunks (含完整 Wiki 元数据)")

        # Step 4: 批量灌入 Chroma 向量数据库并持久化
        vector_db = Chroma.from_documents(
            documents=final_docs,
            embedding=self.embeddings,
            persist_directory=self.persist_directory,
        )
        print(f"🎉 入库圆满完成！数据已落盘至：{self.persist_directory}")
        return vector_db


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wiki 结构感知向量库批量入库工程")
    parser.add_argument("--wiki-dir", default=str(WIKI_DIR), help="Wiki 卡片目录")
    parser.add_argument("--persist-dir", default=str(INDEXING_OUTPUT / "chroma_db"), help="Chroma 持久化目录")
    parser.add_argument("--model", default="", help="Embedding 模型名(默认取 EMBED_MODEL 或 qwen3-embedding-8b)")
    parser.add_argument(
        "--query",
        default="电脑能上QQ但打不开网页，提示DNS解析失败，员工该如何自助处理？",
        help="入库后用于验证的检索问题",
    )
    args = parser.parse_args()

    provider = KspEmbeddingProvider(
        cache_dir=str(Path(args.persist_dir).parent / ".emb_cache"),
        model_override=args.model or None,
    )
    pipeline = WikiKnowledgeIngestionPipeline(
        persist_directory=args.persist_dir,
        embedding_provider=provider,
    )
    db = pipeline.process_and_ingest_dir(args.wiki_dir)

    # 验证元数据检索
    print(f"\n🔍 测试提问：{args.query}")
    results = db.similarity_search(args.query, k=1)
    if results:
        print(f"🎯 命中片段：\n{results[0].page_content}")
        print(f"🏷️ 附带元数据：\n{results[0].metadata}")
