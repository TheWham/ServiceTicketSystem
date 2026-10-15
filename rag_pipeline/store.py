"""Chroma 向量库管理器：全量重建 + manifest 构建指纹落盘（含无 chromadb 时的纯内存/SQLite 兼容兜底）。"""

import json
import math
import shutil
import sqlite3
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .chunking.structure_aware import Document
from .embedding import KspEmbeddingProvider

try:
    from langchain_community.vectorstores import Chroma
    import chromadb
except ImportError:
    Chroma = None
    chromadb = None


class SimpleVectorStore:
    """当环境未安装 chromadb 时提供的轻量兼容向量库（支持直接读取已有 chroma.sqlite3 或内存余弦检索）。"""

    def __init__(self, documents: List[Document], embeddings: List[List[float]], embedding_provider: KspEmbeddingProvider):
        self.documents = documents
        self.embeddings = embeddings
        self.embedding_provider = embedding_provider
        self._fallback_doc_embeddings: Optional[List[List[float]]] = None

    @classmethod
    def from_documents(
        cls,
        documents: List[Document],
        embedding: KspEmbeddingProvider,
        collection_name: str = "",
        persist_directory: Optional[str] = None,
    ) -> "SimpleVectorStore":
        vecs = embedding.embed_documents([d.page_content for d in documents])
        return cls(documents=documents, embeddings=vecs, embedding_provider=embedding)

    @classmethod
    def from_chroma_sqlite(cls, persist_directory: str, embedding_provider: KspEmbeddingProvider) -> Optional["SimpleVectorStore"]:
        db_file = Path(persist_directory) / "chroma.sqlite3"
        if not db_file.exists():
            return None
        try:
            conn = sqlite3.connect(str(db_file))
            cur = conn.cursor()
            rows = cur.execute("SELECT vector, metadata FROM embeddings_queue ORDER BY seq_id").fetchall()
            conn.close()
            if not rows:
                return None
            docs: List[Document] = []
            vecs: List[List[float]] = []
            for raw_vec, raw_meta in rows:
                meta = json.loads(raw_meta) if raw_meta else {}
                text = meta.pop("chroma:document", "")
                dim = len(raw_vec) // 4
                vec = list(struct.unpack(f"<{dim}f", raw_vec))
                docs.append(Document(page_content=text, metadata=meta))
                vecs.append(vec)
            return cls(documents=docs, embeddings=vecs, embedding_provider=embedding_provider)
        except Exception:
            return None

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (na * nb)

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        # 若离线模式且当前 query 未命中真实模型向量缓存，保证 query 与 doc 使用同一兜底向量空间计算余弦，防止跨空间失真
        use_fallback_space = (
            not self.embedding_provider.available
            and self.embedding_provider._cache_get(query) is None
        )
        q_vec = self.embedding_provider.embed_query(query)
        if use_fallback_space:
            if self._fallback_doc_embeddings is None:
                self._fallback_doc_embeddings = [
                    self.embedding_provider._fallback_vector(d.page_content, dim=self.embedding_provider.dim)
                    for d in self.documents
                ]
            doc_vecs = self._fallback_doc_embeddings
        else:
            doc_vecs = self.embeddings

        scored: List[Tuple[Document, float]] = []
        for doc, vec in zip(self.documents, doc_vecs):
            if filter and not all(doc.metadata.get(fk) == fv for fk, fv in filter.items()):
                continue
            scored.append((doc, self._cosine(q_vec, vec)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        return [d for d, _ in self.similarity_search_with_relevance_scores(query, k=k, filter=filter)]


class VectorStoreManager:
    """负责两套对照向量数据库的初始化、持久化与检索。"""

    def __init__(self, base_persist_dir: str, embedding_provider: KspEmbeddingProvider):
        self.base_dir = Path(base_persist_dir)
        self.embedding_provider = embedding_provider

    def build_store(self, collection_name: str, documents: List[Document], persist_subdir: str,
                    manifest: Optional[Dict[str, Any]] = None):
        """把一批 Document 向量化并落盘到独立子目录，返回可检索的向量库句柄。"""
        target_dir = self.base_dir / persist_subdir
        if Chroma is not None:
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
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            print(f"       -> 正在构建内存向量库 [{collection_name}] (共 {len(documents)} 个 Chunks)...")
            db = SimpleVectorStore.from_documents(
                documents=documents,
                embedding=self.embedding_provider,
                collection_name=collection_name,
                persist_directory=str(target_dir)
            )
        if manifest is not None:
            with open(target_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        return db
