"""Chroma 向量库管理器：全量重建 + manifest 构建指纹落盘。"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

try:
    from langchain_community.vectorstores import Chroma
    import chromadb
except ImportError:
    Chroma = None
    chromadb = None

from .embedding import KspEmbeddingProvider


class VectorStoreManager:
    """负责两套对照向量数据库的初始化、持久化与检索。

    为什么 build_store 每次先删旧目录再重建：
    教学/实验场景下切块策略会反复调整（如改 chunk_size、改切分算法），
    若增量追加会让旧策略的残留切片污染新库，导致评测结果不可复现。
    因此每次全量重建，保证"库里只有当前策略的产物"。
    """
    def __init__(self, base_persist_dir: str, embedding_provider: KspEmbeddingProvider):
        self.base_dir = Path(base_persist_dir)
        self.embedding_provider = embedding_provider

    def build_store(self, collection_name: str, documents: List[Document], persist_subdir: str,
                    manifest: Optional[Dict[str, Any]] = None) -> Chroma:
        """把一批 Document 向量化并落盘到独立子目录，返回可检索的 Chroma 句柄。

        manifest：可选的构建指纹（wiki 内容哈希 + 切块参数 + 嵌入模型），落盘为
        manifest.json，供下游（Day 13）加载前做语料一致性校验。"""
        target_dir = self.base_dir / persist_subdir
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"       -> 正在构建 [{collection_name}] (共 {len(documents)} 个 Chunks)...")
        db = Chroma.from_documents(
            documents=documents,
            embedding=self.embedding_provider,
            collection_name=collection_name,
            persist_directory=str(target_dir)
        )
        if manifest is not None:
            with open(target_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        return db


# ==============================================================================
# 4. 黄金业务对抗问答集与评测打分体系
# ==============================================================================
