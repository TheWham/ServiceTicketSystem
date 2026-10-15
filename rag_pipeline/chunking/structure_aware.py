"""Wiki 结构感知切块（对照策略）与朴素固定长度切块（基线）。"""

import os
import re
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import yaml

try:
    from langchain_core.documents import Document
except ImportError:
    @dataclass
    class Document:  # type: ignore
        page_content: str
        metadata: Dict[str, Any] = field(default_factory=dict)

try:
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
except ImportError:
    class MarkdownHeaderTextSplitter:  # type: ignore
        """轻量 Markdown 标题切分器兜底（未安装 langchain_text_splitters 时使用）。"""
        def __init__(self, headers_to_split_on: List[Tuple[str, str]], strip_headers: bool = False):
            self.headers = sorted(headers_to_split_on, key=lambda x: len(x[0]), reverse=True)
            self.strip_headers = strip_headers

        def split_text(self, text: str) -> List[Document]:
            docs: List[Document] = []
            cur_meta: Dict[str, str] = {}
            cur_lines: List[str] = []
            for ln in text.splitlines():
                matched = False
                for prefix, name in self.headers:
                    if ln.startswith(prefix + " "):
                        if cur_lines:
                            docs.append(Document(page_content="\n".join(cur_lines).strip(), metadata=dict(cur_meta)))
                            cur_lines = []
                        cur_meta[name] = ln[len(prefix) + 1:].strip()
                        if not self.strip_headers:
                            cur_lines.append(ln)
                        matched = True
                        break
                if not matched:
                    cur_lines.append(ln)
            if cur_lines:
                docs.append(Document(page_content="\n".join(cur_lines).strip(), metadata=dict(cur_meta)))
            return [d for d in docs if d.page_content]

    class RecursiveCharacterTextSplitter:  # type: ignore
        """轻量递归字符切分器兜底（未安装 langchain_text_splitters 时使用）。"""
        def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, separators: Optional[List[str]] = None):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

        def create_documents(self, texts: List[str]) -> List[Document]:
            out: List[Document] = []
            step = max(self.chunk_size - self.chunk_overlap, 1)
            for t in texts:
                for start in range(0, len(t), step):
                    piece = t[start:start + self.chunk_size]
                    if piece:
                        out.append(Document(page_content=piece, metadata={}))
                    if start + self.chunk_size >= len(t):
                        break
            return out

        def split_documents(self, docs: List[Document]) -> List[Document]:
            out: List[Document] = []
            for d in docs:
                for sub in self.create_documents([d.page_content]):
                    sub.metadata = dict(d.metadata)
                    out.append(sub)
            return out


class WikiStructureAwareChunker:
    """
    结构感知切块引擎（自适应粒度）：
    - YAML Frontmatter 自动解析与清洗
    - 短卡片整卡保持原子性（卡片即最小语义单元，落在 300~800 token 甜点区）
    - 长文档才降级：标题树粗切 -> 相邻小节合并到目标粒度 -> 递归微切兜底
    - 全局业务属性 Payload 深度注入
    """
    def __init__(self, chunk_size: int = 550, chunk_overlap: int = 80, max_card_chars: int = 1000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_card_chars = max_card_chars

        self.headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
        ]
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )

        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "；", " ", ""]
        )

    @staticmethod
    def parse_wiki_frontmatter(file_content: str) -> Tuple[Dict[str, Any], str]:
        """分离 YAML Frontmatter 与 Markdown 正文"""
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.search(frontmatter_pattern, file_content, re.DOTALL)
        if match:
            yaml_text = match.group(1)
            try:
                metadata = yaml.safe_load(yaml_text) or {}
            except Exception:
                metadata = {}
            body_content = file_content[match.end():]
            return metadata, body_content
        return {}, file_content

    def _merge_small_sections(self, splits: List[Document]) -> List[Document]:
        """把过小的相邻标题节向上合并到目标粒度（只在标题边界合并，不切断句子）。"""
        merged: List[Document] = []
        cur: Optional[Document] = None
        for doc in splits:
            if cur is None:
                cur = doc
                continue
            if len(cur.page_content) + len(doc.page_content) <= self.chunk_size:
                cur = Document(
                    page_content=cur.page_content + "\n\n" + doc.page_content,
                    metadata={**cur.metadata, **{k: v for k, v in doc.metadata.items() if k not in cur.metadata}},
                )
            else:
                merged.append(cur)
                cur = doc
        if cur is not None:
            merged.append(cur)
        return merged

    def split_wiki_document(self, file_path: str) -> List[Document]:
        """对单个 Wiki 文档执行自适应粒度切块与元数据注入。"""
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        frontmatter_meta, body = self.parse_wiki_frontmatter(raw_content)
        wiki_title = frontmatter_meta.get("title", Path(file_path).stem)

        if len(body) <= self.max_card_chars:
            header_splits = [Document(page_content=body, metadata={"Header_1": wiki_title})]
            oversized = False
        else:
            raw_splits = self.header_splitter.split_text(body)
            header_splits = self._merge_small_sections(raw_splits)
            oversized = True

        final_chunks: List[Document] = []
        for header_doc in header_splits:
            if oversized and len(header_doc.page_content) > self.chunk_size:
                sub_splits = self.recursive_splitter.split_documents([header_doc])
            else:
                sub_splits = [header_doc]
            for idx, chunk in enumerate(sub_splits):
                h1 = chunk.metadata.get("Header_1", "")
                h2 = chunk.metadata.get("Header_2", "")
                h3 = chunk.metadata.get("Header_3", "")
                breadcrumbs = " > ".join([h for h in [h1, h2, h3] if h])

                if breadcrumbs:
                    enhanced_content = f"【制度大纲：{breadcrumbs}】\n{chunk.page_content}"
                else:
                    enhanced_content = f"【制度归属：{wiki_title}】\n{chunk.page_content}"
                chunk.page_content = enhanced_content

                for k, v in frontmatter_meta.items():
                    chunk.metadata[f"wiki_{k}"] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
                chunk.metadata.setdefault("wiki_status", "现行")

                chunk.metadata["source_file"] = os.path.basename(file_path)
                chunk.metadata["chunk_id"] = str(uuid.uuid4())[:8]
                chunk.metadata["sub_idx"] = idx
                chunk.metadata["chunk_length"] = len(chunk.page_content)
                chunk.metadata["split_strategy"] = (
                    "Card-Atomic (Wiki卡片整卡原子 + 元数据注入)" if not oversized
                    else "Structure-Aware (Wiki Header + 元数据注入)"
                )

                final_chunks.append(chunk)

        return final_chunks


class NaiveFixedChunker:
    """对照组：传统朴素暴力切块"""
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

    def split_raw_document(self, file_path: str) -> List[Document]:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        docs = self.splitter.create_documents([raw_content])
        for idx, doc in enumerate(docs):
            doc.metadata = {
                "source_file": os.path.basename(file_path),
                "chunk_id": str(uuid.uuid4())[:8],
                "sub_idx": idx,
                "split_strategy": "Naive-Fixed-Cut (No Structure, No Metadata)"
            }
        return docs
