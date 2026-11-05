#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingest_vector_store.py — 基于 Wiki 结构与元数据注入的向量库批量入库工程
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

from rag_pipeline.config import load_config, build_chunker, WIKI_DIR, INDEXING_OUTPUT
from rag_pipeline.embedding import KspEmbeddingProvider
from rag_pipeline.store import SimpleVectorStore
from rag_pipeline.chunking.structure_aware import Document, WikiStructureAwareChunker


class WikiKnowledgeIngestionPipeline:
    """读取带 YAML Frontmatter 的 Wiki 卡片，注入元数据后批量灌入 Chroma。"""

    def __init__(
        self,
        persist_directory: str = str(INDEXING_OUTPUT / "chroma_db"),
        embedding_provider: KspEmbeddingProvider = None,
        chunk_size: int = 550,
        chunk_overlap: int = 80,
    ):
        self.persist_directory = persist_directory
        self.cfg = load_config()

        print("⚡ 正在加载 Embedding 模型...")
        self.embeddings = embedding_provider or KspEmbeddingProvider(
            cache_dir=str(Path(persist_directory).parent / ".emb_cache")
        )
        print(f"   -> Embedding 引擎: 【{self.embeddings.engine_type}】")

        self.chunker, self.use_parent_child = build_chunker(self.cfg)

    def process_and_ingest_dir(self, wiki_dir: str):
        wiki_path = Path(wiki_dir)
        files = sorted(wiki_path.glob("*.md"))
        files = [f for f in files if f.name != "_index.md"]
        if not files:
            raise FileNotFoundError(f"❌ 未在 {wiki_path} 找到任何 .md Wiki 卡片")

        print(f"📖 正在解析企业 Wiki 卡片目录：{wiki_path}（共 {len(files)} 张）...")
        final_docs: List[Document] = []
        for fp in files:
            if self.use_parent_child:
                _, chunks = self.chunker.split_wiki_document(str(fp))
            else:
                chunks = self.chunker.split_wiki_document(str(fp))
            final_docs.extend(chunks)
            print(f"   - {fp.name} -> {len(chunks)} 个结构化切片")

        print(f"✅ 成功拆解为 {len(final_docs)} 个高纯度结构化 Chunks (含完整 Wiki 元数据)")

        if Chroma is not None:
            vector_db = Chroma.from_documents(
                documents=final_docs,
                embedding=self.embeddings,
                persist_directory=self.persist_directory,
            )
        else:
            vector_db = SimpleVectorStore.from_documents(
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

    print(f"\n🔍 测试提问：{args.query}")
    results = db.similarity_search(args.query, k=1)
    if results:
        print(f"🎯 命中片段：\n{results[0].page_content}")
        print(f"🏷️ 附带元数据：\n{results[0].metadata}")
