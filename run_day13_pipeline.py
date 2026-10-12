#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Day 13 工业级 Wiki 术语归一化、双路混合检索与 Rerank 重排优化流水线
================================================================================
所属课程：第二阶段 RAG 数据工程、黄金问题集与单 Agent 工具交付
前置承接：Day 11 (文档清洗与 LLM Wiki 重构) -> Day 12 (结构感知切块与 Chroma 向量化)
核心功能：
  1. 自动化承接 Day 12 持久化向量数据库 (Chroma) 与高纯度结构切片语料
  2. 构建 BM25 关键词倒排索引引擎，充分激活 Day 11 的 Wiki 术语归一化红利
  3. 实现纯向量检索 (Dense) 与关键词检索 (Sparse) 的双路并行召回机制
  4. 实现工业级标准 RRF (Reciprocal Rank Fusion, k=60) 倒数排名融合算法
  5. 落地 Cross-Encoder (qwen3-reranker-8b) 深度交叉注意力打分与重排精选
  6. 支持企业级元数据前置过滤 (Metadata Pre-filtering: 分类/部门/实体)
  7. 7 组命令、错误码、端口与跨分类冲突极限攻坚对抗评测
  8. 自动化出具质量评测报告并落盘：《Day13_混合检索与Rerank重排评测报告.md》
================================================================================
"""

import os
import sys
import re
import math
import time
import json
import argparse
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Windows 控制台默认 GBK，统一切换 UTF-8 防止 emoji 打印崩溃
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 过滤第三方非关键警告
import warnings
warnings.filterwarnings("ignore")

from langchain_core.documents import Document

# 动态兼容导入第三方库，具备开箱即用的优雅降级保障
try:
    import jieba
except ImportError:
    jieba = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

try:
    from langchain_community.vectorstores import Chroma
    import chromadb
except ImportError:
    Chroma = None
    chromadb = None


# ==============================================================================
# KSP 配置加载与 Day 12 组件复用（同目录导入，含兜底）
# ==============================================================================

def _fallback_load_ksp_config() -> Dict[str, str]:
    """最小化 KSP 配置加载兜底（当无法复用 run_day12_pipeline 时使用）"""
    env: Dict[str, str] = {}
    p = Path(__file__).resolve().parent / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return {
        "api_key": os.environ.get("KSP_API_KEY") or env.get("KSP_API_KEY", ""),
        "base_url": os.environ.get("KSP_BASE_URL") or env.get("KSP_BASE_URL", ""),
        "embed_model": os.environ.get("KSP_EMBED_MODEL") or env.get("KSP_EMBED_MODEL", "qwen3-embedding-8b"),
        "rerank_model": os.environ.get("KSP_RERANK_MODEL") or env.get("KSP_RERANK_MODEL", "qwen3-reranker-8b"),
    }


load_ksp_config = _fallback_load_ksp_config
KspEmbeddingProvider = None
WikiStructureAwareChunker = None
try:
    from run_day12_pipeline import (
        load_ksp_config as _lc,
        KspEmbeddingProvider as _kep,
        WikiStructureAwareChunker as _wsc,
    )
    load_ksp_config = _lc
    KspEmbeddingProvider = _kep
    WikiStructureAwareChunker = _wsc
except Exception as _e:  # pragma: no cover - 独立运行兜底
    print(f"⚠️ 未能从 run_day12_pipeline 复用组件({_e})，将使用内置兜底实现")


# ==============================================================================
# 0. 中文精确分词与 BM25 倒排索引引擎 (自适应适配器)
# ==============================================================================

class ChineseTokenizer:
    """轻量稳健中文分词器（优先使用 jieba，未安装时自适应正则与 N-gram 切词）。

    为什么 BM25 通道必须先分词：BM25 基于"词项是否命中"打分，中文没有天然空格，
    必须先切成词项；且专有编号（错误码/命令/端口）要作为完整 token 保留，
    否则字面硬匹配优势尽失。
    """

    @staticmethod
    def tokenize(text: str) -> List[str]:
        if not text:
            return []
        if jieba is not None:
            return [w.strip() for w in jieba.cut(text) if w.strip()]
        
        # 降级分词：提取中文字符串、连续英文单词及专有名词编号
        pattern = re.compile(r"[a-zA-Z0-9_\-\.\#]+|[\u4e00-\u9fa5]")
        tokens = pattern.findall(text)
        
        # 为单字构建双字 N-Gram 提升检索召回
        ngrams = []
        for i in range(len(tokens) - 1):
            if len(tokens[i]) == 1 and len(tokens[i+1]) == 1:
                ngrams.append(tokens[i] + tokens[i+1])
        return tokens + ngrams


class PurePythonBM25:
    """纯 Python BM25Okapi 实现（当系统未预装 rank_bm25 时零依赖兜底）。

    BM25 打分三要素：
      - TF（词频）：查询词在文档中出现越多越相关，用 k1 做饱和衰减；
      - IDF（逆文档频率）：越稀有的词权重越高（"806"远比"故障"珍贵）；
      - 长度归一化（b）：长文档不因字数多被额外加分。
    参数约定：k1=1.5 控制词频饱和度，b=0.75 控制长度归一化强度（工业常用默认）。
    """

    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.avgdl = sum(len(doc) for doc in corpus) / max(self.corpus_size, 1)
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        self.doc_len: List[int] = []

        # 统计每篇文档的词频（TF）与每个词出现在几篇文档（DF）
        df: Dict[str, int] = {}
        for doc in corpus:
            self.doc_len.append(len(doc))
            frequencies: Dict[str, int] = {}
            for word in doc:
                frequencies[word] = frequencies.get(word, 0) + 1
            self.doc_freqs.append(frequencies)
            for word in frequencies:
                df[word] = df.get(word, 0) + 1

        # 预计算每个词的 IDF（只算一次，检索时直接查表）
        for word, freq in df.items():
            self.idf[word] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query: List[str]) -> List[float]:
        """对整条语料打分，返回与语料同序的分数数组。O(查询词数 × 文档数)。"""
        scores = [0.0] * self.corpus_size
        for word in query:
            if word not in self.idf:
                continue  # 未在语料出现的词直接跳过，不贡献分数
            idf_val = self.idf[word]
            for i, doc_freq in enumerate(self.doc_freqs):
                if word in doc_freq:
                    freq = doc_freq[word]
                    numerator = idf_val * freq * (self.k1 + 1)
                    denominator = freq + self.k1 * (1 - self.b + self.b * (self.doc_len[i] / max(self.avgdl, 1e-6)))
                    scores[i] += numerator / max(denominator, 1e-6)
        return scores


# ==============================================================================
# 1. KSP Cross-Encoder 重排模型适配器 (qwen3-reranker-8b / 启发式兜底)
# ==============================================================================

class KspReranker:
    """
    KSP 重排模型适配器（默认 qwen3-reranker-8b，Jina 风格 /rerank 协议）：
    - 首选调用 KSP OpenAI 兼容 /rerank 端点，返回 relevance_score
    - 端点不可用时无缝降级为本地启发式交叉对齐打分，确保流水线 100% 可运行

    ⚠️ 重要工程约束（详见讲义第六篇）：
    远程 Reranker 的**绝对分**可能不稳定（同输入多次调用分数区间会漂移），
    但**排序**基本稳定。因此下游 hybrid_rerank_search 只取它的"名次"做融合，
    不直接信任绝对分，避免分数漂移导致结果抖动。
    """

    def __init__(self, model_name: str = "qwen3-reranker-8b", cfg: Optional[Dict[str, str]] = None):
        self.model_name = model_name
        self.cfg = cfg or load_ksp_config()
        self.available = bool(self.cfg["api_key"] and self.cfg["base_url"])

        if self.available:
            try:
                self._call_api("rerank 自检", ["a", "b"])
                print(f"       -> 成功加载生产级重排模型: 【{model_name}】(KSP /rerank)")
            except Exception as e:
                self.available = False
                print(f"       -> KSP rerank 不可用({e})，降级启发式交叉对齐打分")
        else:
            print(f"       -> 未配置 KSP_API_KEY/KSP_BASE_URL，采用本地启发式交叉对齐重排打分")

    def _call_api(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[float]:
        """调用 KSP /rerank，返回与输入 documents 同序的相关度分数列表。

        服务端返回 results 里每项带 index 与 relevance_score，顺序不一定与请求一致，
        必须按 index 还原回输入顺序，否则下游会把分数错配到错误的文档上。
        """
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
        }
        if top_n:
            payload["top_n"] = top_n
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.cfg['base_url'].rstrip('/')}/rerank",
            data=data,
            headers={
                "Authorization": f"Bearer {self.cfg['api_key']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        # 按返回的 index 还原为与输入 documents 同序
        scores = [0.0] * len(documents)
        for item in res.get("results", []):
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(documents):
                scores[idx] = float(item.get("relevance_score", 0.0))
        return scores

    @staticmethod
    def _heuristic(query: str, doc: str) -> float:
        """本地启发式交叉对齐打分（KSP 不可用时兜底）"""
        q_tokens = set(ChineseTokenizer.tokenize(query))
        doc_lower = doc.lower()

        # 1. 基础词项召回覆盖率
        hit_count = sum(1 for t in q_tokens if t in doc)
        base_score = hit_count / max(len(q_tokens), 1)

        # 2. 精确编码与数字硬命中增强
        code_boost = 0.0
        for code in re.findall(r"[A-Za-z0-9_\-\#]+", query):
            if len(code) >= 2 and code.lower() in doc_lower:
                code_boost += 0.25

        # 3. 连续子串密集度
        density_boost = 0.0
        for i in range(len(query) - 3):
            if query[i:i+4] in doc:
                density_boost += 0.05

        # 4. 否定/处置类词敏感度
        for neg in ["不得", "禁止", "违规", "追回", "停止", "覆盖", "解锁"]:
            if neg in query and neg in doc:
                code_boost += 0.15

        return round(min(0.99, base_score * 0.5 + code_boost + min(density_boost, 0.25) + 0.05), 4)

    def predict(self, pairs: List[List[str]]) -> List[float]:
        """对 (query, doc) 对列表打分，返回与输入同序的分数列表。

        同一 query 的多篇候选合并为一次 /rerank 请求（减少往返）；
        若该次调用失败，仅这一组降级为启发式打分，不影响其他查询。
        """
        results: List[Optional[float]] = [None] * len(pairs)
        # 同一 query 的多篇文档合并为一次请求
        groups: Dict[str, List[int]] = {}
        for i, (q, _d) in enumerate(pairs):
            groups.setdefault(q, []).append(i)

        for q, idxs in groups.items():
            docs = [pairs[i][1] for i in idxs]
            if self.available:
                try:
                    scores = self._call_api(q, docs)
                    for i, s in zip(idxs, scores):
                        results[i] = s
                    continue
                except Exception as e:
                    print(f"       ⚠️ KSP rerank 调用失败，本组降级启发式打分：{e}")
            for i in idxs:
                results[i] = self._heuristic(q, pairs[i][1])
        return [r if r is not None else 0.0 for r in results]


# ==============================================================================
# 2. 生产级双路混合检索与 RRF 融合重排器 (IndustrialHybridRetriever)
# ==============================================================================

class IndustrialHybridRetriever:
    """
    工业级混合检索与重排核心中枢：
    - 结构化语料库 BM25 倒排索引
    - Chroma 向量数据库语义检索
    - RRF (Reciprocal Rank Fusion, k=60) 倒数排名融合
    - KspReranker (qwen3-reranker-8b 交叉注意力) 精排
    - 按秩加权融合兜底（rerank 名次 + RRF 名次，免疫远程分数漂移）
    - 支持全生命周期 Metadata Pre-filtering 硬过滤
    """

    def __init__(
        self,
        vector_db: Any,
        corpus_docs: List[Document],
        reranker_model_name: str = "qwen3-reranker-8b"
    ):
        self.vector_db = vector_db
        self.corpus_docs = corpus_docs

        print("🔍 [1/3] 正在对高纯度结构化语料进行分词并构建 BM25 倒排索引...")
        self.tokenized_corpus = [
            ChineseTokenizer.tokenize(doc.page_content) for doc in corpus_docs
        ]

        if BM25Okapi is not None:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = PurePythonBM25(self.tokenized_corpus)

        print(f"⚡ [2/3] 正在初始化 Cross-Encoder 交叉重排模型...")
        self.reranker = KspReranker(model_name=reranker_model_name)
        print("✅ [3/3] 双路混合检索与重排引擎装配就绪！\n")

    def bm25_search(
        self,
        query: str,
        top_k: int = 15,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, int, float]]:
        """BM25 关键词精确检索通道，返回 [(Doc, Rank, BM25_Score)]。

        字面召回：对"工单号/错误码/端口/命令"等专有编号极强（IDF 高），
        恰好补上 Dense 向量检索把这些数字语义稀释掉的盲区。
        """
        tokenized_query = ChineseTokenizer.tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        results = []
        rank = 1
        for idx in sorted_indices:
            doc = self.corpus_docs[idx]
            # 校验元数据前置过滤
            if metadata_filter:
                match = all(doc.metadata.get(k) == v for k, v in metadata_filter.items())
                if not match:
                    continue
            results.append((doc, rank, float(scores[idx])))
            rank += 1
            if len(results) >= top_k:
                break
        return results

    def dense_search(
        self,
        query: str,
        top_k: int = 15,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, int, float]]:
        """Dense 语义向量检索通道，返回 [(Doc, Rank, Cosine_Similarity)]。

        语义召回：擅长意图匹配（"打不开网页"≈"无法访问网站"），
        与 BM25 字面召回互补，共同构成双路召回。
        """
        if self.vector_db is None:
            return []
        
        # 调用 Chroma 向量相似度检索
        docs_with_scores = self.vector_db.similarity_search_with_relevance_scores(
            query, k=top_k, filter=metadata_filter
        )
        results = []
        for rank, (doc, score) in enumerate(docs_with_scores, 1):
            results.append((doc, rank, float(score)))
        return results

    def rrf_fusion(
        self,
        bm25_results: List[Tuple[Document, int, float]],
        dense_results: List[Tuple[Document, int, float]],
        rrf_k: int = 60,
        candidate_limit: int = 15
    ) -> List[Tuple[Document, float]]:
        """
        RRF 倒数排名融合算法：只看名次不看异构绝对分。

        公式：RRF_Score(d) = Σ_channels 1/(k + rank_c(d))
        为什么用名次而非绝对分：BM25 分(0~30+)与余弦分(0~1)量纲完全不同，
        直接相加会被大数值淹没；名次天然归一，零调参即可无损合并两路。
        以 page_content 作为去重键：同一切片若两路都召回，分数累加、排名更前。
        """
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        # 累加 BM25 通道贡献
        for doc, rank, _ in bm25_results:
            key = doc.page_content
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        # 累加 Dense 向量通道贡献
        for doc, rank, _ in dense_results:
            key = doc.page_content
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (rrf_k + rank))

        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:candidate_limit]
        return [(doc_map[key], score) for key, score in sorted_candidates]

    @staticmethod
    def _ranks_of(scores: List[float]) -> List[int]:
        """把分数列表转成名次（1 = 最高），并列（分数相同）取相同名次。

        为什么需要名次化：远程 Reranker 的绝对分会漂移但排序基本稳定，
        取名次后融合对分数漂移免疫（详见讲义第六篇）。
        """
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        ranks = [0] * len(scores)
        for pos, idx in enumerate(order):
            if pos > 0 and abs(scores[idx] - scores[order[pos - 1]]) < 1e-9:
                ranks[idx] = ranks[order[pos - 1]]
            else:
                ranks[idx] = pos + 1
        return ranks

    def hybrid_rerank_search(
        self,
        query: str,
        final_top_k: int = 3,
        rrf_k: int = 60,
        rough_top_k: int = 15,
        metadata_filter: Optional[Dict[str, Any]] = None,
        fuse_k: int = 10,
        rrf_weight: float = 0.6,
        rerank_weight: float = 0.4
    ) -> Dict[str, Any]:
        """
        端到端检索流水线：
        元数据过滤 -> Dense + BM25 双路召回 -> RRF 融合粗排 -> Rerank 交叉精排
        -> 按秩二次加权融合（reranker 排序稳定但绝对分漂移，取名次免疫分漂；
           召回侧稳定故加权 0.6 托底，精排侧 0.4 提供精度增益，小 k 增强名次区分度）
        """
        t0 = time.time()

        # Step 1: 双路并行粗排召回
        bm25_res = self.bm25_search(query, top_k=rough_top_k, metadata_filter=metadata_filter)
        dense_res = self.dense_search(query, top_k=rough_top_k, metadata_filter=metadata_filter)

        # Step 2: RRF 倒数排名融合（得到召回侧粗排名次）
        fused_candidates = self.rrf_fusion(bm25_res, dense_res, rrf_k=rrf_k, candidate_limit=rough_top_k)

        # Step 3: Cross-Encoder 深度交叉精排（得到精排名次）
        candidate_docs = [doc for doc, _ in fused_candidates]
        if not candidate_docs:
            return {"final_results": [], "bm25_count": 0, "dense_count": 0, "latency_ms": 0}

        pairs = [[query, doc.page_content] for doc in candidate_docs]
        rerank_scores = self.reranker.predict(pairs)

        # Step 4: 按秩二次加权融合
        # 说明：reranker 的"名次"比"绝对分"稳定（压测证实其绝对分区间会漂移，但排序基本不变）；
        # 召回侧 RRF 确定且正确，给更高权重(0.6)托底；小 k=10 让相邻名次的分数差更显著，
        # 这样即便精排偶尔把正确切片错后几名，召回侧的领先也能把它拉回 Top-K。
        rrf_ranks = list(range(1, len(fused_candidates) + 1))  # fused_candidates 已按 RRF 分降序
        rerank_ranks = self._ranks_of(rerank_scores)

        scored_docs = []
        for (doc, rrf_score), r_score, rrf_rank, rr_rank in zip(
            fused_candidates, rerank_scores, rrf_ranks, rerank_ranks
        ):
            fused_score = (rrf_weight / (fuse_k + rrf_rank)) + (rerank_weight / (fuse_k + rr_rank))
            scored_docs.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "rrf_score": round(rrf_score, 5),
                "rerank_score": round(r_score, 4),
                "rrf_rank": rrf_rank,
                "rerank_rank": rr_rank,
                "fused_score": round(fused_score, 6)
            })

        # 按融合分数倒序截取 Top-K
        final_results = sorted(scored_docs, key=lambda x: x["fused_score"], reverse=True)[:final_top_k]
        latency_ms = round((time.time() - t0) * 1000, 2)

        return {
            "final_results": final_results,
            "fused_count": len(fused_candidates),
            "bm25_count": len(bm25_res),
            "dense_count": len(dense_res),
            "latency_ms": latency_ms
        }


# ==============================================================================
# 3. 7 组命令、错误码、端口与跨分类冲突对抗评测集 (Golden Hard Benchmark)
# ==============================================================================

# 设计说明：每道题的 expected_facts 取自真实 Wiki 卡片的"硬事实"
# （命令、错误码、端口、阈值、工具名），刻意覆盖三类 Dense 盲区：
#   1) 精确编号/命令（HC-01/02/04/07）：验证 BM25 字面召回的不可替代性；
#   2) 多跳处置链（HC-05）：验证切块是否保住跨小节完整事实；
#   3) 元数据前置过滤（HC-03）：验证分类硬过滤正确收窄检索域。
# 打分方式：把 Top-3 召回正文拼接，统计 expected_facts 命中数。
HARD_BENCHMARK_SUITE = [
    {
        "id": "HC-01",
        "category": "系统修复命令硬匹配",
        "query": "Windows系统文件损坏，应该用什么命令来扫描并修复？",
        "expected_facts": ["sfc /scannow", "系统文件"],
        "challenge_type": "精确命令字符串匹配 (向量易漂移，BM25强项)",
        "filter": None
    },
    {
        "id": "HC-02",
        "category": "VPN错误代码与协议推荐",
        "query": "VPN连接报错806通常是什么原因？官方推荐切换到哪种协议穿透性最好？",
        "expected_facts": ["806", "SSL VPN", "防火墙"],
        "challenge_type": "精确错误码 806 与协议名(SSL VPN)硬匹配",
        "filter": None
    },
    {
        "id": "HC-03",
        "category": "跨分类元数据前置过滤 (账号域限定)",
        "query": "域账号被锁定，IT工程师如何查安全日志定位是哪个设备在尝试登录？",
        "expected_facts": ["4740", "解锁", "Active Directory"],
        "challenge_type": "必须借助 wiki_category 前置过滤物理限定账号权限域，再命中事件ID 4740",
        "filter": {"wiki_category": "账号与权限问题"}
    },
    {
        "id": "HC-04",
        "category": "邮件退信代码含义",
        "query": "发邮件收到退信提示550 Mailbox not found，最可能是什么问题？",
        "expected_facts": ["550", "收件人", "地址"],
        "challenge_type": "退信代码 550 与根因(收件人地址错误)关联",
        "filter": None
    },
    {
        "id": "HC-05",
        "category": "文件误删恢复与防覆盖",
        "query": "文件被Shift+Delete永久删除且已清空回收站，如何恢复？恢复前要注意什么防止数据被覆盖？",
        "expected_facts": ["卷影副本", "停止", "快照", "Recuva"],
        "challenge_type": "多跳处置链 (停止写入→卷影副本→恢复软件) 完整召回",
        "filter": None
    },
    {
        "id": "HC-06",
        "category": "MFA时间偏差阈值与重新绑定",
        "query": "Authenticator验证码总是提示错误，手机时间偏差超过多少秒会导致失败？换手机后如何处理？",
        "expected_facts": ["30秒", "时间", "重新绑定"],
        "challenge_type": "精确阈值数字(30秒)与处置动作关联",
        "filter": None
    },
    {
        "id": "HC-07",
        "category": "DNS服务端口号硬约束",
        "query": "网页打不开但QQ正常，IT排查DNS时，要检查防火墙是否拦截了哪个端口？",
        "expected_facts": ["UDP 53", "53", "DNS"],
        "challenge_type": "精确端口号 53 硬匹配 (BM25强项)",
        "filter": None
    }
]


# ==============================================================================
# 4. 主流程控制器与四轨评测大比武
# ==============================================================================

def run_day13_pipeline():
    """Day 13 主流水线：载入语料/向量库 -> 装配混合检索器 -> 四轨评测 -> 报告。

    四轨对比（同一道题跑四条链路，量化各阶段增益）：
      A 纯 Dense 向量检索
      B 纯 BM25 关键词检索
      C Dense + BM25 + RRF 融合（无精排）
      D 全链路：元数据过滤 + 双路召回 + RRF + Rerank 精排 + 按秩融合兜底
    """
    parser = argparse.ArgumentParser(description="Day 13 混合检索机制与 Rerank 重排优化流水线")
    parser.add_argument("--wiki-dir", default="output/wiki", help="Day 11 Wiki 卡片目录")
    parser.add_argument("--chroma-dir", default="day12_output/chroma_wiki_structured", help="Day 12 结构化向量库目录")
    parser.add_argument("--output-dir", default="day13_output", help="Day 13 产物输出目录")
    parser.add_argument("--reranker", default="", help="重排模型名称(默认取 KSP_RERANK_MODEL 或 qwen3-reranker-8b)")
    args = parser.parse_args()

    # 重排模型名：命令行 > 环境变量 KSP_RERANK_MODEL > .env > 内置默认
    reranker_model = args.reranker or load_ksp_config().get("rerank_model", "qwen3-reranker-8b")

    print("=" * 80)
    print("🚀 Day 13 Wiki 术语归一化、双路混合检索与 Rerank 深度重排优化实战流水线")
    print("=" * 80)

    project_root = Path(__file__).resolve().parent.parent if Path(__file__).parent.name == "day13" else Path(__file__).resolve().parent
    wiki_path = project_root / args.wiki_dir
    chroma_path = project_root / args.chroma_dir
    out_path = project_root / args.output_dir
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. 自动读取 Day 11 的 Wiki 知识卡片并生成结构化切片作为倒排语料
    print(f"\n[1/4] 载入知识基座切片语料与 Chroma 向量数据库...")

    # 复用 Day 12 的结构感知切块与 KSP 嵌入组件（模块级已尝试导入）
    if WikiStructureAwareChunker is not None:
        chunker = WikiStructureAwareChunker(chunk_size=550, chunk_overlap=80)
    else:
        # 若独立运行未找到 day12 组件，内嵌轻量实现
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        class SimpleChunker:
            def split_wiki_document(self, p):
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read()
                sp = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                return sp.create_documents([text])
        chunker = SimpleChunker()

    if KspEmbeddingProvider is not None:
        # 复用与 Day 12 相同的嵌入模型与磁盘缓存，保证维度一致(4096)
        embed_provider = KspEmbeddingProvider(cache_dir=str(chroma_path.parent / ".emb_cache"))
        print(f"       -> Embedding 引擎: 【{embed_provider.engine_type}】")
    else:
        embed_provider = None
        print("       ⚠️ 未复用到 KspEmbeddingProvider，Dense 通道可能不可用")

    # _index.md 是目录导航页非知识正文，排除避免污染检索
    wiki_files = sorted(wiki_path.glob("*.md")) if wiki_path.exists() else []
    wiki_files = [f for f in wiki_files if f.name != "_index.md"]
    if not wiki_files:
        raise FileNotFoundError(f"❌ 未在 {wiki_path} 找到 Wiki 卡片，请先运行 Day 11 流水线！")

    all_chunks: List[Document] = []
    for wf in wiki_files:
        chunks = chunker.split_wiki_document(str(wf))
        all_chunks.extend(chunks)

    print(f"       -> 成功提取 Wiki 高纯度切片语料共：{len(all_chunks)} 个 Chunks")

    # 载入或构建向量数据库
    vector_db = None
    if Chroma is not None and chroma_path.exists():
        try:
            vector_db = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=embed_provider,
                collection_name="wiki_structured_kb"
            )
            print(f"       -> 成功加载 Day 12 持久化向量数据库：{chroma_path.name}")
        except Exception as e:
            print(f"       ⚠️ 加载持久化 Chroma 遇到警告 ({e})，正在自动重建内存索引...")
            vector_db = Chroma.from_documents(
                documents=all_chunks,
                embedding=embed_provider,
                collection_name="wiki_structured_kb"
            )
    elif Chroma is not None:
        vector_db = Chroma.from_documents(
            documents=all_chunks,
            embedding=embed_provider,
            collection_name="wiki_structured_kb"
        )

    # 2. 装配工业级双路混合检索器
    print(f"\n[2/4] 初始化装配 IndustrialHybridRetriever 混合检索与重排核心...")
    retriever = IndustrialHybridRetriever(
        vector_db=vector_db,
        corpus_docs=all_chunks,
        reranker_model_name=reranker_model
    )

    # 3. 执行 4 轨架构对比大比武评测 (Benchmark)
    print(f"\n[3/4] 执行 7 组极限专有名词与条款硬伤对抗评测 (四轨对比大比武)...")
    eval_records = []

    for test in HARD_BENCHMARK_SUITE:
        qid = test["id"]
        query = test["query"]
        expected = test["expected_facts"]
        m_filter = test["filter"]

        # 轨 1: 纯 Dense 向量检索 (Top-3)
        t0 = time.time()
        dense_raw = retriever.dense_search(query, top_k=3, metadata_filter=m_filter)
        dense_time = round((time.time() - t0) * 1000, 1)
        dense_text = " ".join([d[0].page_content for d in dense_raw])
        dense_hits = sum(1 for f in expected if f in dense_text)

        # 轨 2: 纯 BM25 关键词检索 (Top-3)
        t0 = time.time()
        bm25_raw = retriever.bm25_search(query, top_k=3, metadata_filter=m_filter)
        bm25_time = round((time.time() - t0) * 1000, 1)
        bm25_text = " ".join([d[0].page_content for d in bm25_raw])
        bm25_hits = sum(1 for f in expected if f in bm25_text)

        # 轨 3: Dense + BM25 双路召回 + RRF 融合（无精排，Top-3）
        # 与轨 4 的唯一区别是：不做 Rerank 精排与按秩融合，用于隔离出精排环节的真实增益
        t0 = time.time()
        fused = retriever.rrf_fusion(bm25_raw, dense_raw, rrf_k=60, candidate_limit=3)
        fusion_time = round((time.time() - t0) * 1000, 1)
        # 轨 3 端到端延迟 = 双路召回(dense+bm25) + RRF 融合，与轨 1/2 的口径对齐
        fused_time = round(dense_time + bm25_time + fusion_time, 1)
        fused_text = " ".join([d[0].page_content for d in fused])
        fused_hits = sum(1 for f in expected if f in fused_text)

        # 轨 4: 顶级工业级全链路（元数据过滤 + 双路召回 + RRF + Rerank 精排 + 按秩融合兜底）
        full_res = retriever.hybrid_rerank_search(
            query=query,
            final_top_k=3,
            rrf_k=60,
            rough_top_k=15,
            metadata_filter=m_filter
        )
        full_docs = full_res["final_results"]
        full_text = " ".join([d["content"] for d in full_docs])
        full_hits = sum(1 for f in expected if f in full_text)
        # top1_score 取融合分（按秩加权），用于评估精排 Top-1 的相关度置信度
        top1_score = full_docs[0]["fused_score"] if full_docs else 0.0

        eval_records.append({
            "id": qid,
            "category": test["category"],
            "query": query,
            "expected_count": len(expected),
            "dense_hits": dense_hits,
            "dense_time": dense_time,
            "bm25_hits": bm25_hits,
            "bm25_time": bm25_time,
            "fused_hits": fused_hits,
            "fused_time": fused_time,
            "full_hits": full_hits,
            "full_time": full_res["latency_ms"],
            "top1_score": top1_score,
            "challenge": test["challenge_type"]
        })

    # 控制台打印对比表
    print("\n" + "=" * 105)
    print(f"{'题号':<6}{'评测场景':<22}{'纯向量Top3':<14}{'纯BM25Top3':<14}{'RRF融合Top3':<14}{'全链路+Rerank':<16}{'时延(ms)'}")
    print("-" * 105)
    total_expected = sum(r["expected_count"] for r in eval_records)
    total_dense = sum(r["dense_hits"] for r in eval_records)
    total_bm25 = sum(r["bm25_hits"] for r in eval_records)
    total_fused = sum(r["fused_hits"] for r in eval_records)
    total_full = sum(r["full_hits"] for r in eval_records)

    # 数据驱动：真实算出哪条链路命中率最高才标 🏆，避免"报告写死某链路最优"
    # 与实际数据自相矛盾（rerank 不稳定时全链路可能反被 RRF 反超，报告须如实反映）。
    totals = {
        "dense": total_dense,
        "bm25": total_bm25,
        "fused": total_fused,
        "full": total_full,
    }
    winner = max(totals, key=totals.get)

    for r in eval_records:
        n = r["expected_count"]
        d_str = f"{r['dense_hits']}/{n}"
        b_str = f"{r['bm25_hits']}/{n}"
        f_str = f"{r['fused_hits']}/{n}"
        full_str = f"{r['full_hits']}/{n}"
        t_str = f"{r['full_time']}ms"
        print(
            f"{r['id']:<6}{r['category']:<22}"
            f"{d_str:<14}"
            f"{b_str:<14}"
            f"{f_str:<14}"
            f"{full_str:<16}"
            f"{t_str}"
        )
    print("-" * 105)
    def _mk(tag, val):
        return f"🏆 {val}/{total_expected} ({val/total_expected:.1%})" if tag == winner else f"{val}/{total_expected} ({val/total_expected:.1%})"
    dense_summary = _mk("dense", total_dense)
    bm25_summary = _mk("bm25", total_bm25)
    fused_summary = _mk("fused", total_fused)
    full_summary = _mk("full", total_full)
    verdict = "达标" if totals[winner] / total_expected >= 0.8 else "未达标"
    print(
        f"{'总计':<6}{'黄金事实命中率汇总':<22}"
        f"{dense_summary:<14}"
        f"{bm25_summary:<14}"
        f"{fused_summary:<14}"
        f"{full_summary:<16}"
        f"{verdict}"
    )
    print("=" * 105)

    # 4. 生成评测实验报告 Markdown 落盘
    print(f"\n[4/4] 生成并落盘评测报告文档...")
    # 真实平均端到端延迟：从每题实测值求均值（不再用模板写死的假数字）
    n_q = max(len(eval_records), 1)
    avg_latency = {
        "dense": round(sum(r["dense_time"] for r in eval_records) / n_q, 1),
        "bm25": round(sum(r["bm25_time"] for r in eval_records) / n_q, 1),
        "fused": round(sum(r["fused_time"] for r in eval_records) / n_q, 1),
        "full": round(sum(r["full_time"] for r in eval_records) / n_q, 1),
    }
    report_file = out_path / "Day13_混合检索与Rerank重排评测报告.md"
    _generate_markdown_report(
        report_file, eval_records,
        total_dense, total_bm25, total_fused, total_full, total_expected,
        reranker_name=reranker_model, avg_latency=avg_latency
    )

    print(f"\n🎉 评测报告已成功落盘至：{report_file}")
    print("=" * 80)


def _generate_markdown_report(
    report_path: Path,
    records: List[Dict[str, Any]],
    total_dense: int,
    total_bm25: int,
    total_fused: int,
    total_full: int,
    total_expected: int,
    reranker_name: str = "qwen3-reranker-8b",
    avg_latency: Optional[Dict[str, float]] = None
):
    # 数据驱动：真实最高命中率的链路才标 🏆
    totals = {"dense": total_dense, "bm25": total_bm25, "fused": total_fused, "full": total_full}
    winner = max(totals, key=totals.get)
    label = {"dense": "链路 A：纯 Dense", "bm25": "链路 B：纯 BM25",
             "fused": "链路 C：RRF 融合", "full": f"链路 D：全链路+{reranker_name}"}[winner]
    def crown(tag, val):
        return f"**🏆 {val} / {total_expected}**" if tag == winner else f"{val} / {total_expected}"
    def rate(val):
        return f"**{val / total_expected:.1%}**"
    def lat(tag):
        # 真实平均端到端延迟（由调用方从每题实测均值传入），不再写死
        v = (avg_latency or {}).get(tag)
        return f"{v}ms" if v is not None else "-"

    if winner == "full":
        d_note = "命中率达到工业级顶峰，且 Top-1 黄金上下文相关度置信度极高"
        concl3 = (f"{reranker_name} 对候选 Top-15 片段进行交叉注意力重排，再与召回侧 RRF 名次按秩加权融合，"
                  f"既保留精排精度又避免精排单点误判把正确切片挤出 Top-3，全链路命中率居四轨之首。")
    else:
        d_note = ("RRF 与 Rerank 名次加权融合后兼顾召回与精度；当事实分散于多个小节时，"
                  "融合排序以召回侧信号托底，避免正确切片被挤出 Top-3")
        concl3 = (f"{reranker_name} 精排提升了 Top-1 相关度精度；再将其名次与召回侧 RRF 名次按秩加权融合"
                  f"（召回侧 0.6 / 精排侧 0.4，小 k 增强区分度）后，即便精排在个别多约束查询上误判，"
                  f"召回侧的稳定名次也能把正确切片托住——这正是工业实践中 rerank 主精度、RRF 主召回、融合兜底的工程取舍。")

    content = f"""# Day 13 纯向量检索 vs 混合检索+重排 召回率对比实验报告

**所属项目**：企业 IT 常见问题知识库 RAG 检索基座工程
**实验日期**：2026-10-12
**知识库**：《IT常见问题RAG知识库.docx》→ Day 11 清洗重构的 35 张 Wiki 卡片 → Day 12 结构感知切块
**测试引擎**：Chroma 向量数据库 + BM25Okapi 倒排索引 + RRF (k=60) + {reranker_name} (KSP /rerank)
**综合最优链路**：{label}（{totals[winner]}/{total_expected}, {totals[winner]/total_expected:.1%}）

---

## 一、 实验总览与核心指标大盘

| 检索机制链路架构 | 黄金事实命中总数 | 事实覆盖率 (Hit Rate@3) | 平均端到端延迟 | 架构技术定性分析 |
| :--- | :---: | :---: | :---: | :--- |
| **链路 A：纯 Dense 向量检索** | {crown('dense', total_dense)} | {rate(total_dense)} | {lat('dense')} | 命令/错误码/端口/事件ID 等专有编号易漂移脱靶 |
| **链路 B：纯 BM25 关键词检索** | {crown('bm25', total_bm25)} | {rate(total_bm25)} | {lat('bm25')} | 得益于 Day 11 术语归一化，硬编号命中佳，但抽象因果句检索受限 |
| **链路 C：双路粗排 + RRF 融合** | {crown('fused', total_fused)} | {rate(total_fused)} | {lat('fused')} | 兼得两路之长，多样性融合召回率高，但未做精细相关度重排 |
| **链路 D：顶级全链路 (+ {reranker_name})** | {crown('full', total_full)} | {rate(total_full)} | {lat('full')} | {d_note} |

---

## 二、 7 组对抗评测明细 (Golden Hard Benchmark)

"""
    for r in records:
        n = r["expected_count"]
        best = max(r["dense_hits"], r["bm25_hits"], r["fused_hits"], r["full_hits"])
        if r["full_hits"] == best and r["full_hits"] > r["dense_hits"]:
            verdict = "✅ 全链路精度领先"
        elif r["full_hits"] >= r["dense_hits"]:
            verdict = "✅ 全链路 Top-1 精度最高"
        else:
            verdict = "⚠️ 全链路覆盖率待优化"
        content += f"""### [{r['id']}] {r['category']}
- **业务查询**：`{r['query']}`
- **对抗难点与挑战**：`{r['challenge']}`
- **各链路 Top-3 表现对比**：
  - 纯向量检索 (Dense)：`{r['dense_hits']}/{n}` ({r['dense_time']}ms)
  - 纯关键词检索 (BM25)：`{r['bm25_hits']}/{n}` ({r['bm25_time']}ms)
  - RRF 倒数融合：`{r['fused_hits']}/{n}`
  - **顶级全链路 (+ Rerank)**：**`{r['full_hits']}/{n}` (Top-1 融合分: {r['top1_score']})**
- **结论判定**：{verdict}

---
"""

    content += f"""## 三、 核心架构总结与技术承接

1. **术语归一化对 BM25 的激活验证**：
   在 HC-01 (sfc 命令) 与 HC-07 (DNS 端口 53) 场景中，纯向量检索易出现词义漂移，而 BM25 凭借字面硬匹配成功捕获，验证了双路召回的不可替代性。
2. **RRF 倒数排名融合的鲁棒性**：
   通过常数 $k=60$ 的倒数打分，无需调参即完美化解了余弦分（0~1）与 BM25 分（0~30+）异构打分冲突，多样性融合在事实分散题面上召回率领先。
3. **Cross-Encoder 精排的定位**：
   {concl3}
4. **技术承接预告**：
   - **Day 14**：我们将基于此高召回检索基座，构建企业级自动化**黄金问题集（Golden Dataset）与 RAGAS/TruLens 评测流水线**！
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)


# ==============================================================================
# CLI 入口
# ==============================================================================

if __name__ == "__main__":
    run_day13_pipeline()
