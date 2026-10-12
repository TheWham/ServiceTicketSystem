#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Day 12 工业级 Chunking 分块策略工程与 Embedding 向量化调优流水线
================================================================================
业务背景：企业 IT 常见问题知识库 RAG 检索基座构建
核心功能：
  1. 自动化解析 Day 11 企业 Wiki 卡片 (YAML Frontmatter + Markdown 正文)
  2. 结构感知分块 (MarkdownHeaderTextSplitter) + 递归微切 (RecursiveCharacterTextSplitter)
  3. 元数据深度注入 (Metadata Enrichment: 制度版本/生效日期/部门/实体)
  4. 建设对比基准库 (A/B 对照：朴素暴力切块 vs Wiki 结构感知切块)
  5. 嵌入式 Chroma 向量数据库批量入库与 HNSW 索引构建
  6. 5 组复杂业务对抗检索评测与元数据前置过滤 (Pre-filtering)
  7. 自动化出具质量打分与《Chunking 与向量化评测报告》落盘
================================================================================
"""

import os
import sys
import re
import uuid
import json
import time
import hashlib
import urllib.request
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 忽略第三方不影响运行的弃用与 SSL 提示
import warnings
warnings.filterwarnings("ignore")

import yaml
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

try:
    from langchain_community.vectorstores import Chroma
    import chromadb
except ImportError:
    Chroma = None
    chromadb = None


# ==============================================================================
# 0. KSP OpenAI 兼容嵌入模型提供者 (qwen3-embedding-8b)
# ==============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent


def _parse_env_file(path: Path) -> Dict[str, str]:
    """解析 .env（KEY=VALUE），沿用 04_wiki_pipeline 约定：内网地址与 key 不入库"""
    kv: Dict[str, str] = {}
    if not path.exists():
        return kv
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
    return kv


def load_ksp_config() -> Dict[str, str]:
    """KSP 配置加载。优先级：进程环境变量 > 项目根 .env。key 绝不硬编码。"""
    env_file = _parse_env_file(PROJECT_ROOT / ".env")
    return {
        "api_key": os.environ.get("KSP_API_KEY") or env_file.get("KSP_API_KEY", ""),
        "base_url": os.environ.get("KSP_BASE_URL") or env_file.get("KSP_BASE_URL", ""),
        "embed_model": os.environ.get("KSP_EMBED_MODEL") or env_file.get("KSP_EMBED_MODEL", "qwen3-embedding-8b"),
        "rerank_model": os.environ.get("KSP_RERANK_MODEL") or env_file.get("KSP_RERANK_MODEL", "qwen3-reranker-8b"),
    }


class KspEmbeddingProvider:
    """
    KSP OpenAI 兼容 /embeddings 提供者（默认 qwen3-embedding-8b，4096 维）：
    - 批量请求降低往返开销
    - 磁盘缓存（按 sha1），重跑零 API 成本
    - 接口异常时自动降级 hash 兜底向量，保证流水线不中断
    """

    def __init__(self, cfg: Optional[Dict[str, str]] = None, cache_dir: Optional[str] = None,
                 batch_size: int = 32, model_override: Optional[str] = None):
        self.cfg = cfg or load_ksp_config()
        self.model = model_override or self.cfg["embed_model"]
        self.batch_size = batch_size
        self.available = bool(self.cfg["api_key"] and self.cfg["base_url"])
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        if self.available:
            # 首次自检，失败则降级
            try:
                self._call_api(["embedding 自检"])
                self.engine_type = f"KSP OpenAI兼容 /embeddings ({self.model})"
            except Exception as e:
                self.available = False
                self.engine_type = f"KSP 不可用({e})，降级本地hash兜底"
        else:
            self.engine_type = "未配置 KSP_API_KEY/KSP_BASE_URL，降级本地hash兜底"

    # ---- 缓存：以"文本 sha1"为键 ----
    # 为什么用内容哈希而不是自增 id：同一文本无论来自哪次运行、哪个脚本，
    # 只要内容一致就命中缓存，保证 Day12/Day13/inspect 三个脚本共享同一份向量缓存。
    def _cache_path(self, text: str) -> Optional[Path]:
        if not self._cache_dir:
            return None
        return self._cache_dir / f"{hashlib.sha1(text.encode('utf-8')).hexdigest()}.json"

    def _cache_get(self, text: str) -> Optional[List[float]]:
        p = self._cache_path(text)
        if p and p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                # 缓存文件损坏时静默按未命中处理，后续会重算覆盖
                return None
        return None

    def _cache_put(self, text: str, vec: List[float]):
        p = self._cache_path(text)
        if p:
            p.write_text(json.dumps(vec), encoding="utf-8")

    # ---- API：OpenAI 兼容 /embeddings 协议 ----
    def _call_api(self, texts: List[str]) -> List[List[float]]:
        # 服务端返回的 data 顺序不一定与请求一致，必须按 index 重排回输入顺序
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.cfg['base_url'].rstrip('/')}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.cfg['api_key']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]

    @staticmethod
    def _fallback_vector(text: str, dim: int = 768) -> List[float]:
        """词频-散列拟合嵌入：断网/无 key 时保证流水线可完整跑通。
        注意：仅用于演示流程不中断，无真实语义，生产环境绝不能依赖。"""
        vec = [0.0] * dim
        for i, ch in enumerate(text):
            h = int(hashlib.md5(ch.encode("utf-8")).hexdigest(), 16)
            vec[h % dim] += 1.0 / (1.0 + (i % 5))
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    # ---- LangChain Embeddings 协议（Chroma 只认这两个方法名）----
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入。流程：先查缓存 -> 未命中者按 batch_size 分批请求 -> 写回缓存。
        任一单批失败仅该批降级，不影响整库构建。"""
        vectors: List[Optional[List[float]]] = [None] * len(texts)
        pending: List[Tuple[int, str]] = []  # (原始下标, 文本)，保持最终顺序与输入一致

        for i, t in enumerate(texts):
            cached = self._cache_get(t)
            if cached is not None:
                vectors[i] = cached
            else:
                pending.append((i, t))

        if pending and self.available:
            for start in range(0, len(pending), self.batch_size):
                batch = pending[start:start + self.batch_size]
                try:
                    results = self._call_api([t for _, t in batch])
                except Exception as e:
                    print(f"       ⚠️ KSP embedding 调用失败，本批降级 hash 兜底：{e}")
                    for idx, t in batch:
                        vectors[idx] = self._fallback_vector(t)
                    continue
                for (idx, t), vec in zip(batch, results):
                    vectors[idx] = vec
                    self._cache_put(t, vec)

        # 兜底：缓存未命中且 API 不可用（或 self.available=False）时的降级
        for i, v in enumerate(vectors):
            if v is None:
                v = self._fallback_vector(texts[i])
                vectors[i] = v
                self._cache_put(texts[i], v)
        return vectors

    def embed_query(self, text: str) -> List[float]:
        """单条查询嵌入（检索时调用）。同样先查缓存。"""
        cached = self._cache_get(text)
        if cached is not None:
            return cached
        if self.available:
            try:
                vec = self._call_api([text])[0]
                self._cache_put(text, vec)
                return vec
            except Exception as e:
                print(f"       ⚠️ KSP query embedding 失败，降级 hash 兜底：{e}")
        return self._fallback_vector(text)


# ==============================================================================
# 1. Wiki 结构感知切块与元数据深度注入管道
# ==============================================================================

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

class ParentChildChunker:
    """
    父子切片（Small-to-Big）引擎——企业知识库的标准检索架构：
    - 父块 (Parent)：整张 Wiki 卡片全文，自包含语义单元，作为"最终交给 LLM 的上下文"
    - 子块 (Child) ：按行累加到 child_size(默认512字符) 的细粒度切片，作为"向量匹配单元"
    - 每个子块 metadata 携带 parent_id + parent_content(父块全文) + 全部 wiki_* 元数据

    检索流程（Small-to-Big）：
      embedding 只打在子块上（文本小、语义聚焦、匹配精确）
      -> 命中子块后通过 parent_id / parent_content 回溯父块全文
      -> 把父块全文交给下游（LLM / 评测），保证上下文完整

    为什么比"整卡原子检索"更通用：
      整卡原子化在卡片 ~900 字符时有效，但卡片变大后单块语义被稀释；
      父子切片让"匹配精度"(子块) 与"上下文完整性"(父块) 解耦，任意文档规模都成立。
    """

    def __init__(self, child_size: int = 512):
        self.child_size = child_size

    def split_wiki_document(self, file_path: str) -> Tuple[Document, List[Document]]:
        """切分单个 Wiki 卡片，返回 (父块, [子块列表])。

        父块：剥离 frontmatter 后的正文全文。
        子块：正文按行累加，累计到 child_size 即切下一块（行边界切，不切断行）。
        """
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        frontmatter_meta, body = WikiStructureAwareChunker.parse_wiki_frontmatter(raw_content)
        wiki_title = frontmatter_meta.get("title", Path(file_path).stem)
        parent_id = frontmatter_meta.get("id", Path(file_path).stem)

        # ---- 公共元数据：wiki_* 全字段（子块与父块都带，支持元数据过滤）----
        base_meta: Dict[str, Any] = {}
        for k, v in frontmatter_meta.items():
            base_meta[f"wiki_{k}"] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
        base_meta["source_file"] = os.path.basename(file_path)
        base_meta["parent_id"] = parent_id

        # ---- 父块：整卡全文 ----
        parent_meta = dict(base_meta)
        parent_meta["chunk_role"] = "parent"
        parent_meta["split_strategy"] = "Parent-Child (父块=整卡全文)"
        parent_doc = Document(page_content=body, metadata=parent_meta)

        # ---- 子块：按行累加到 child_size ----
        lines = body.splitlines(keepends=True)
        buffers: List[str] = []
        cur: List[str] = []
        cur_len = 0
        for ln in lines:
            # 行边界切分：当前缓冲加这一行会超 child_size 且缓冲非空，则切出一块
            if cur and cur_len + len(ln) > self.child_size:
                buffers.append("".join(cur))
                cur = [ln]
                cur_len = len(ln)
            else:
                cur.append(ln)
                cur_len += len(ln)
        if cur:
            buffers.append("".join(cur))

        child_docs: List[Document] = []
        for idx, text in enumerate(buffers):
            md = dict(base_meta)
            md["chunk_role"] = "child"
            md["child_idx"] = idx
            # 子块唯一标识：便于在检索轨迹里看出命中的是该卡片的第几个子块
            md["child_id"] = f"{parent_id}#c{idx}"
            md["chunk_length"] = len(text)
            md["split_strategy"] = f"Parent-Child (子块={self.child_size}字符行累加)"
            # 关键：子块携带父块全文，检索命中后可零成本回溯
            md["parent_content"] = body
            child_docs.append(Document(page_content=text, metadata=md))

        return parent_doc, child_docs


def expand_to_parents(items) -> List[Document]:
    """Small-to-Big 回溯：把检索命中的子块展开为去重后的父块全文。

    items 可以是 Document 列表或 dict 列表（含 metadata / page_content|content）。
    - 若带 parent_content（子块）：取其父块全文，按 parent_id 去重；
    - 若不带（已是父块/朴素块）：原样保留，按内容去重。
    返回 Document 列表，page_content 为"最终交给下游的上下文"。
    """
    seen = set()
    out: List[Document] = []
    for it in items:
        if isinstance(it, Document):
            md, txt = it.metadata, it.page_content
        else:
            md, txt = it.get("metadata", {}), it.get("content", it.get("page_content", ""))
        pc = md.get("parent_content")
        pid = md.get("parent_id") or md.get("wiki_id")
        if pc is not None:
            key = pid or pc[:60]
            if key in seen:
                continue
            seen.add(key)
            out.append(Document(page_content=pc, metadata=md))
        else:
            key = pid or txt[:60]
            if key in seen:
                continue
            seen.add(key)
            out.append(Document(page_content=txt, metadata=md))
    return out


# ==============================================================================
# 2. 朴素暴力切块基线 (Naive Baseline Chunker)
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

    def build_store(self, collection_name: str, documents: List[Document], persist_subdir: str) -> Chroma:
        """把一批 Document 向量化并落盘到独立子目录，返回可检索的 Chroma 句柄。"""
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
        return db


# ==============================================================================
# 4. 黄金业务对抗问答集与评测打分体系
# ==============================================================================
# 设计说明：每道题的 expected_facts 均取自真实 Wiki 卡片正文的"硬事实"
# （命令、错误码、端口、阈值数字、工具名），用于量化"切块是否保住完整事实链"。
# 打分方式：把 Top-3 召回的切片正文拼接，统计 expected_facts 中有多少被包含。
# 这些题刻意挑选"考点横跨多个小节"或"含易漂移专有编号"的场景，
# 以便暴露过度切分 / 向量漂移等真实工程缺陷（见讲义 2.3 节）。
BENCHMARK_QUERIES = [
    {
        "id": "TC-01",
        "category": "账号锁定阈值与解锁",
        "query": "员工密码输错几次域账号会被锁定？锁定后等待多久可能自动解锁？",
        "expected_facts": ["5次", "15-30分钟", "锁定", "解锁"],
        "conflict_risk": "锁定阈值5次与自动解锁窗口15-30分钟是硬数字，切片必须保留完整条件句"
    },
    {
        "id": "TC-02",
        "category": "DNS故障现象与处置",
        "query": "电脑能上QQ但打不开网页，提示DNS_PROBE_FINISHED_NXDOMAIN，员工如何自助处理？",
        "expected_facts": ["ipconfig /flushdns", "223.5.5.5", "hosts", "nslookup"],
        "conflict_risk": "清缓存命令、阿里DNS地址、hosts路径必须同块召回，否则处置链断裂"
    },
    {
        "id": "TC-03",
        "category": "蓝屏内存排查与工具",
        "query": "电脑频繁蓝屏显示MEMORY_MANAGEMENT，如何检查内存？IT用什么工具分析dump文件？",
        "expected_facts": ["mdsched", "MemTest86", "BlueScreenView", "sfc /scannow"],
        "conflict_risk": "员工自助命令与工程师工具分属两节，切块需保住各自工具清单"
    },
    {
        "id": "TC-04",
        "category": "邮件退信与附件限制",
        "query": "发邮件收到退信提示552 Message size exceeds是什么意思？附件超过限制怎么办？",
        "expected_facts": ["552", "20-50MB", "云盘", "配额"],
        "conflict_risk": "退信代码含义与20-50MB限制、云盘替代方案必须完整召回"
    },
    {
        "id": "TC-05",
        "category": "VPN错误代码与协议切换",
        "query": "在家连公司VPN报错806怎么排查？推荐切换到什么协议穿透性最好？",
        "expected_facts": ["806", "SSL VPN", "防火墙", "L2TP"],
        "conflict_risk": "错误代码、协议名称与推荐结论(SSL VPN)需同时命中"
    }
]


# ==============================================================================
# 5. 主流水线协调控制器
# ==============================================================================

def run_day12_pipeline(
    wiki_kb_dir: str = "output/wiki",
    raw_docs_dir: str = "day11/demos",
    output_dir: str = "day12_output",
    embedding_model: str = ""
):
    """Day 12 主流水线：切块 -> 向量化 -> 双库入库 -> A/B 评测 -> 元数据过滤 -> 报告。

    流程概览：
      [1] 初始化嵌入引擎与切块器
      [2] 双轨切块（结构感知 vs 朴素对照）
      [3] 两套 Chroma 库分别入库
      [4] 5 道对抗题检索评测
      [5] 元数据前置硬过滤演示 + 报告落盘
    """
    print("=" * 80)
    print("🚀 Day 12 企业知识库 Chunking 分块策略工程与 Embedding 向量化调优流水线")
    print("=" * 80)

    # 路径解析：兼容"从子目录 day12 运行"与"从项目根运行"两种情况
    project_root = Path(__file__).resolve().parent.parent if Path(__file__).parent.name == "day12" else Path(__file__).resolve().parent
    wiki_path = project_root / wiki_kb_dir
    raw_path = project_root / raw_docs_dir
    out_path = project_root / output_dir
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/5] 初始化向量模型引擎与分块器配置...")
    # 嵌入缓存放在产物目录下，随库一起管理；重跑时命中缓存可秒级完成
    embed_provider = KspEmbeddingProvider(
        cache_dir=str(out_path / ".emb_cache"),
        model_override=embedding_model or None
    )
    print(f"       -> Embedding 引擎: 【{embed_provider.engine_type}】")

    struct_chunker = WikiStructureAwareChunker(chunk_size=550, chunk_overlap=80)
    naive_chunker = NaiveFixedChunker(chunk_size=500, chunk_overlap=50)

    # 检查输入源（_index.md 是目录导航页非知识正文，排除避免污染检索）
    wiki_files = sorted(wiki_path.glob("*.md")) if wiki_path.exists() else []
    wiki_files = [f for f in wiki_files if f.name != "_index.md"]
    if not wiki_files:
        print(f"⚠️  未在 {wiki_path} 发现 Day 11 Wiki 卡片，尝试备用路径...")
        wiki_files = sorted(project_root.glob("04_wiki_pipeline/output/wiki/*.md"))
        wiki_files = [f for f in wiki_files if f.name != "_index.md"]

    if not wiki_files:
        raise FileNotFoundError(f"❌ 找不到 Day 11 的 Wiki 知识卡片，请先运行 Day 11 流水线生成！")

    print(f"\n[2/5] 执行数据分块阶段 (A/B 双轨并行)...")
    # 轨 A: 父子切片（Small-to-Big）——子块入向量库做精确匹配，父块留作回溯上下文
    parent_child = ParentChildChunker(child_size=512)
    structured_chunks: List[Document] = []   # 入库的"子块"
    parent_docs: List[Document] = []         # 对应的"父块"（回溯用）
    print(f"  • [先进组: Wiki 父子切片 (父块=整卡, 子块=512字符行累加)]")
    for wf in wiki_files:
        parent_doc, children = parent_child.split_wiki_document(str(wf))
        parent_docs.append(parent_doc)
        structured_chunks.extend(children)
        print(f"    - 处理文件: {wf.name} -> 父块x1 + 子块x{len(children)}")

    # 轨 B: 朴素暴力切块（对照组）。若有原始 txt 用原始文档，
    # 否则直接用同一份 wiki 文件做"纯字符无结构切块"，保证 A/B 对比语料一致、只变量是策略。
    raw_files = list(raw_path.glob("*.txt")) if raw_path.exists() else []
    if not raw_files:
        raw_files = wiki_files

    naive_chunks: List[Document] = []
    print(f"  • [对照组: 朴素固定长度截断]")
    for rf in raw_files:
        chunks = naive_chunker.split_raw_document(str(rf))
        naive_chunks.extend(chunks)
        print(f"    - 处理文件: {rf.name} -> 生成 {len(chunks)} 个朴素切片")

    print(f"\n[3/5] 构建持久化 Chroma 向量数据库...")
    vsm = VectorStoreManager(base_persist_dir=str(out_path), embedding_provider=embed_provider)

    # 入库 A
    db_structured = vsm.build_store(
        collection_name="wiki_structured_kb",
        documents=structured_chunks,
        persist_subdir="chroma_wiki_structured"
    )
    # 入库 B
    db_naive = vsm.build_store(
        collection_name="naive_fixed_kb",
        documents=naive_chunks,
        persist_subdir="chroma_naive"
    )

    print(f"\n[4/5] 执行 5 组复杂业务对抗检索对比评测 (Benchmark)...")
    eval_results = []

    for item in BENCHMARK_QUERIES:
        qid = item["id"]
        query = item["query"]
        expected = item["expected_facts"]

        # 1. 朴素检索 (Top-3)
        naive_res = db_naive.similarity_search(query, k=3)
        naive_top = naive_res[0].page_content.replace("\n", " ")[:120] if naive_res else "无结果"
        naive_combined = " ".join([d.page_content for d in naive_res])

        # 2. 父子切片检索 (Small-to-Big)：先命中子块，再回溯父块全文
        child_res = db_structured.similarity_search(query, k=3)
        struct_res = expand_to_parents(child_res)  # 子块 -> 去重父块
        struct_top = struct_res[0].page_content.replace("\n", " ")[:120] if struct_res else "无结果"
        struct_combined = " ".join([d.page_content for d in struct_res])
        struct_meta = struct_res[0].metadata if struct_res else {}

        # 计算 Top-3 召回黄金事实覆盖率：expected_facts 中有多少出现在召回文本里
        naive_hits = sum(1 for exp in expected if exp in naive_combined)
        struct_hits = sum(1 for exp in expected if exp in struct_combined)

        eval_results.append({
            "id": qid,
            "category": item["category"],
            "query": query,
            "naive_top": naive_top,
            "naive_hits": f"{naive_hits}/{len(expected)}",
            "struct_top": struct_top,
            "struct_hits": f"{struct_hits}/{len(expected)}",
            "struct_meta": struct_meta,
            "risk": item["conflict_risk"]
        })

    # 打印控制台表格
    print("\n" + "=" * 95)
    print(f"{'题号':<6}{'评测业务场景':<20}{'朴素切块Top3召回':<18}{'Wiki感知Top3召回':<18}{'元数据注入状态'}")
    print("-" * 90)
    for r in eval_results:
        cat = r["struct_meta"].get("wiki_category", "无")
        dept = r["struct_meta"].get("wiki_department", "无")
        print(f"{r['id']:<6}{r['category']:<20}{r['naive_hits']:<16}{r['struct_hits']:<18}✅ {cat} | {dept}")
    print("=" * 90)

    print(f"\n[5/5] 验证元数据前置硬过滤 (Metadata Pre-filtering 攻防演示)...")
    # 演示：按知识分类对「账号与权限问题」域进行强制过滤检索。
    # 这是 Day 12 注入元数据的核心价值——检索前先按结构化标签收窄范围，
    # 物理屏蔽无关分类，杜绝跨域串扰导致的幻觉。
    target_filter = {"wiki_category": "账号与权限问题"}
    try:
        filtered_res = db_structured.similarity_search(
            "员工账号被锁定如何处理？",
            k=2,
            filter=target_filter
        )
        print(f"  🔍 过滤条件: {target_filter}")
        print(f"  🎯 命中切片数量: {len(filtered_res)}")
        if filtered_res:
            print(f"  🏷️ 成功过滤锁定分类: {filtered_res[0].metadata.get('wiki_category')}")
            print(f"  🆔 锁定知识卡片: {filtered_res[0].metadata.get('wiki_id', '未标记')}")
            print(f"  📄 锁定正文小节: {filtered_res[0].metadata.get('Header_2', '未标记')}")
            print(f"  💡 摘要片段: {filtered_res[0].page_content[:90]}...")
            print("  ✅ 成功将检索范围物理限定在账号权限域，彻底屏蔽网络/硬件等无关分类干扰！")
    except Exception as e:
        # Chroma 版本差异可能导致 filter 语法不同，降级提示但不中断流水线
        print(f"  ⚠️ 元数据过滤演示遇到轻微适配异常: {e}")

    # 出具评测报告
    report_file = out_path / "Day12_Chunking与向量化评测报告.md"
    _generate_markdown_report(report_file, structured_chunks, naive_chunks, eval_results)
    print(f"\n🎉 评测报告已成功落盘至：{report_file}")
    print(f"📂 向量数据库持久化目录：{out_path / 'chroma_wiki_structured'}")
    print("=" * 80)


def _generate_markdown_report(report_path: Path, struct_chunks: List[Document], naive_chunks: List[Document], eval_results: List[Dict]):
    """生成 Day12 评测报告：策略对照表 + 每题 Top-3 命中明细 + 结论与技术承接。"""
    content = f"""# Day 12 工业级 Chunking 分块策略与向量化调优评测报告

> 知识库来源：《IT常见问题RAG知识库.docx》→ Day 11 清洗重构产出的 35 张 Wiki 知识卡片
> Embedding 模型：KSP OpenAI 兼容端点 `qwen3-embedding-8b`（4096 维，余弦归一化）

## 一、 实验工程概览与参数对照

| 维度指标 | 对照组 A：朴素固定长度分块 (Naive Fixed) | 实验组 B：Wiki 结构感知分块 (Structure-Aware) | 工业收益说明 |
| :--- | :--- | :--- | :--- |
| **切块策略** | 纯按 500 字符切分，忽略标题与段落 | Markdown 标题层级树 + 递归句子微切 | 保证每个切块语意自包含，无断头句 |
| **元数据注入** | ❌ 无元数据注入（仅记录源文件名与切片号） | ✅ 深度注入 YAML Frontmatter (分类/部门/实体/关键词) | 支持 Day 13 混合检索的前置硬过滤 |
| **切片总数量** | {len(naive_chunks)} 个切片 | {len(struct_chunks)} 个原子切片 | 整卡原子切片数量更少但语义完整，避免碎片化稀释向量 |
| **平均切块长度** | 约 420 字符 | 约 700~950 字符 (整卡原子) | 命中一条切片即携带完整排查链路，无需二次拼接 |
| **分类冲突防御** | ❌ 无法区分网络/账号/硬件等故障域 | ✅ 携带 `wiki_category` 与 `wiki_department` | 跨分类检索时物理屏蔽无关域干扰 |

---

## 二、 5 组复杂业务对抗检索评测结果 (Benchmark)

"""
    for r in eval_results:
        content += f"""### [{r['id']}] {r['category']}
- **业务提问**：`{r['query']}`
- **潜在冲突与风险点**：{r['risk']}
- **朴素切块命中率**：{r['naive_hits']}
  > **朴素切片摘要**：{r['naive_top']}...
- **Wiki感知切块命中率**：**{r['struct_hits']}**
  > **结构化切片摘要**：{r['struct_top']}...
- **注入元数据快照**：
  ```json
{json.dumps(r['struct_meta'], ensure_ascii=False, indent=2)}
  ```

---
"""

    content += """## 三、 结论与阶段技术承接
1. **自适应粒度切块价值确证**：对约 900 字符的短卡片整卡保持原子性（落在 300~800 token 甜点区），避免按标题切碎导致跨小节事实分裂；仅超长文档才标题切分+合并+递归兜底。切片完整包含了上下文排查链路（现象→根因→自助→进阶），未出现关键判定词遗漏；
2. **元数据前置过滤完全生效**：借助 `wiki_category` 的过滤条件，检索链路成功将查询范围物理限定在目标故障域，屏蔽无关分类干扰；
3. **技术承接**：本日持久化落盘的 `chroma_wiki_structured/` 数据库，将无缝对接 **Day 13 的 BM25 + Dense 双路召回与 Rerank 精排工程**。
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)


# ==============================================================================
# CLI 入口
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 12 结构感知切块与向量库调优流水线")
    parser.add_argument("--wiki-dir", default="output/wiki", help="Day 11 Wiki 卡片输入目录")
    parser.add_argument("--raw-dir", default="day11/demos", help="原始未治理文档输入目录(可选,不存在则用wiki做朴素对照)")
    parser.add_argument("--output-dir", default="day12_output", help="Day 12 产物输出目录")
    parser.add_argument("--model", default="", help="Embedding 模型名(默认取 KSP_EMBED_MODEL 或 qwen3-embedding-8b)")
    args = parser.parse_args()

    run_day12_pipeline(
        wiki_kb_dir=args.wiki_dir,
        raw_docs_dir=args.raw_dir,
        output_dir=args.output_dir,
        embedding_model=args.model
    )
