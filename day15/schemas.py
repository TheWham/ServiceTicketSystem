# -*- coding: utf-8 -*-
"""day15 对外数据模型（Pydantic v2）。

Citation 五字段对齐 docs/Day15_知识库服务层模块整合说明.md 第三节：
chunk_id / source_file / section（面包屑章节）/ snippet / relevance_score。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """结构化溯源：五字段来自检索命中 metadata，永远存在（不依赖 LLM 是否打角标）。"""

    chunk_id: str = Field(description="命中子块 id，如 ITKB-ACC-002#c1")
    source_file: str = Field(default="", description="来源文件名，如 ITKB-ACC-002.md")
    section: str = Field(default="", description="面包屑章节名（H2），如「常见根因」")
    snippet: str = Field(default="", description="命中父卡片段（已压缩空白）")
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    card_id: str = Field(default="", description="父卡 id，如 ITKB-ACC-002")
    title: str = Field(default="", description="卡片标题")
    cited_inline: bool = Field(default=False, description="答案正文是否出现该来源角标")


class TraceCandidate(BaseModel):
    """链路候选明细（来自内核 scored_all），用于网页端漏斗可视化。"""

    chunk_id: str
    card_id: str = ""
    title: str = ""
    section: str = ""
    rrf_rank: Optional[int] = None
    rerank_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    fused_score: Optional[float] = None
    is_final: bool = False
    protected: bool = False


class Trace(BaseModel):
    """一次检索的完整链路快照（数据全部来自 hybrid_rerank_search 的结构化返回）。"""

    bm25_count: int = 0
    dense_count: int = 0
    fused_count: int = 0
    rerank_remote: bool = False
    gate_mode: str = "off"
    gate_margin: float = 0.0
    eff_weights: List[float] = Field(default_factory=list)
    max_rerank_score: float = 0.0
    reject_threshold: Optional[float] = None
    rejected: bool = False
    rewrite_query: Optional[str] = None
    candidates: List[TraceCandidate] = Field(default_factory=list)
    final_ids: List[str] = Field(default_factory=list)
    retrieval_ms: float = 0.0
    llm_ms: float = 0.0
    total_ms: float = 0.0


class ChatRequest(BaseModel):
    """问答入参。query 必填；top_k 缺省走 pipeline.yaml；metadata_filter 做元数据硬过滤。"""

    query: str = Field(min_length=1, max_length=8000)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    metadata_filter: Optional[Dict[str, Any]] = None
    include_trace: bool = True


class ChatResponse(BaseModel):
    """问答出参。

    is_refused=True  → 诚实拒答，answer 为固定拒答文案，citations 为空；
    offline=True     → 离线兜底，answer 为"仅返回检索片段"提示，citations 仍有来源；
    mode             → llm（实时生成）/ cache（命中预热缓存）/ offline / refused。
    """

    query: str
    answer: str
    is_refused: bool = False
    refused_reason: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
    offline: bool = False
    mode: str = "llm"                 # llm | cache | offline | refused
    latency_ms: float = 0.0
    notes: List[str] = Field(default_factory=list)
    trace: Optional[Trace] = None


class ChunkChild(BaseModel):
    """切片演示中的单个子块（Small-to-Big 的匹配单元）。

    preview 为截断预览；content 为完整子块文本（前端点击展开看全文）。
    """

    child_id: str
    section: str = ""
    length: int = 0
    has_boost: bool = False           # 是否含检索增强注入（每卡首块）
    preview: str = ""
    content: str = ""                 # 完整子块文本（前端展开查看全文用）


class ChunkDemoResponse(BaseModel):
    """切片演示出参：父卡（整卡 = 上下文单元）+ 子块列表（= 向量匹配单元）。"""

    card_id: str
    title: str = ""
    source_file: str = ""
    parent_length: int = 0
    parent_preview: str = ""
    children: List[ChunkChild] = Field(default_factory=list)


class CardInfo(BaseModel):
    """卡片清单条目（切片演示下拉与状态统计用）。"""

    card_id: str
    title: str = ""
    category: str = ""
    version: str = ""


class HealthResponse(BaseModel):
    """服务健康回显：装配状态 + 检索/生成可用性 + 缓存与规模统计。"""

    status: str = "UP"                # UP | DEGRADED（DEGRADED 仅表示 wiki→Java 映射未加载）
    chunk_count: int = 0
    wiki_fingerprint: str = ""
    config_fingerprint: str = ""
    rerank_available: bool = False
    rerank_provider: str = "unknown"
    llm_available: bool = False
    llm_model: str = ""
    offline: bool = False
    cached_answers: int = 0
    card_count: int = 0
