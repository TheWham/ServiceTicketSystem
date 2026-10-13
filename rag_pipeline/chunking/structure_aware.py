"""Wiki 结构感知切块（对照策略）与朴素固定长度切块（基线）。"""

import os
import re
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import yaml
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class WikiStructureAwareChunker:
    """
    Day 12 结构感知切块引擎（自适应粒度）：
    - YAML Frontmatter 自动解析与清洗
    - 短卡片整卡保持原子性（卡片即最小语义单元，落在 300~800 token 甜点区）
    - 长文档才降级：标题树粗切 -> 相邻小节合并到目标粒度 -> 递归微切兜底
    - 全局业务属性 Payload 深度注入
    """
    def __init__(self, chunk_size: int = 550, chunk_overlap: int = 80, max_card_chars: int = 1000):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 短于该长度的卡片正文不再按标题切碎，整卡作为一个原子切片
        self.max_card_chars = max_card_chars

        # 标题树切分器
        self.headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
        ]
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )

        # 递归兜底切分器
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
        """把过小的相邻标题节向上合并到目标粒度（只在标题边界合并，不切断句子）。

        为什么需要这一步：MarkdownHeaderTextSplitter 会"逢节必切"，产生大量
        100~300 字符的碎块。若一个完整论点横跨多个小节，碎块会导致检索时事实
        被召回得不完整。这里贪心地把相邻小节累加合并，直到再加就超 chunk_size，
        既保住语义完整性，又不违背标题边界。
        """
        merged: List[Document] = []
        cur: Optional[Document] = None
        for doc in splits:
            if cur is None:
                cur = doc
                continue
            if len(cur.page_content) + len(doc.page_content) <= self.chunk_size:
                # 合并正文；元数据以"先出现的高层标题"为准（cur 在前，优先级更高）
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
        """对单个 Wiki 文档执行自适应粒度切块与元数据注入。

        返回：带 frontmatter 注入与面包屑增强的 Document 列表。
        切分策略二选一：
          - 短卡片（正文 <= max_card_chars）：整卡一个原子切片，不再按标题切碎；
          - 长文档：标题树粗切 -> 相邻小节合并 -> 超长节递归微切兜底。
        """
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        frontmatter_meta, body = self.parse_wiki_frontmatter(raw_content)
        wiki_title = frontmatter_meta.get("title", Path(file_path).stem)

        # ===== 自适应粒度决策：短卡片整卡原子化，长文档才多级切分 =====
        # 设计动机（详见讲义 2.3 节）：~900 字符的短卡片本身就是自包含语义单元，
        # 若按 H2"逢节必切"会把横跨两节的事实切散，导致检索丢考点（TC-03 曾 2/4）。
        if len(body) <= self.max_card_chars:
            # 整卡原子路径：不打标题切分，Header_1 直接用卡片标题
            header_splits = [Document(page_content=body, metadata={"Header_1": wiki_title})]
            oversized = False
        else:
            # 长文档路径：先标题树粗切，再把过小相邻节合并，最后超长节才递归微切
            raw_splits = self.header_splitter.split_text(body)
            header_splits = self._merge_small_sections(raw_splits)
            oversized = True

        final_chunks: List[Document] = []
        for header_doc in header_splits:
            # 二次微切保护（仅长文档路径里仍超预算的节才触发；短卡片路径保持原子不切）
            if oversized and len(header_doc.page_content) > self.chunk_size:
                sub_splits = self.recursive_splitter.split_documents([header_doc])
            else:
                sub_splits = [header_doc]
            for idx, chunk in enumerate(sub_splits):
                # 构造面包屑上下文增强：把"H1 > H2 > H3"层级写进正文开头，
                # 让小模型在向量化时也能感知该切片在原文中的位置（提升语义对齐）
                h1 = chunk.metadata.get("Header_1", "")
                h2 = chunk.metadata.get("Header_2", "")
                h3 = chunk.metadata.get("Header_3", "")
                breadcrumbs = " > ".join([h for h in [h1, h2, h3] if h])

                # 增强前缀（让切片天然带有规约大纲位置）
                if breadcrumbs:
                    enhanced_content = f"【制度大纲：{breadcrumbs}】\n{chunk.page_content}"
                else:
                    enhanced_content = f"【制度归属：{wiki_title}】\n{chunk.page_content}"
                chunk.page_content = enhanced_content

                # 1. 深度注入 Frontmatter 元数据（Day 13 前置硬过滤的基础）
                for k, v in frontmatter_meta.items():
                    # Chroma 等向量数据库要求元数据类型为 str/int/float/bool，
                    # list/dict 一律序列化为 JSON 字符串
                    chunk.metadata[f"wiki_{k}"] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)

                # 2. 注入切块自身拓扑元数据
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


# ==============================================================================
# 1b. 父子切片引擎 (Parent-Child / Small-to-Big)
# ==============================================================================



class NaiveFixedChunker:
    """
    对照组：传统朴素暴力切块
    - 不解析 Frontmatter (将 YAML 当作杂质文本一并切分)
    - 无视 Markdown 标题层级，纯按字符长度死板截断
    - 零业务元数据注入
    """
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


# ==============================================================================
# 3. 双轨向量数据库构建与持久化引擎
# ==============================================================================

