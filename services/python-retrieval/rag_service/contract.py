# -*- coding: utf-8 -*-
"""Java `/api/v1/rag/retrievals` 契约的 Pydantic 镜像。

逐字对齐 origin/main `it-ticket-cloud/rag-service` 的对外 VO 与 consultation-service
`RagServiceKnowledgeRetriever.parse` 的强校验：字段名（camelCase）与值域不得偏离，
否则上游判 INVALID_RESPONSE 且不重试。
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Java OfficeDomain @JsonValue
Domain = Literal["OFFICE_IT", "OFF_TOPIC", "HIGH_RISK", "UNCERTAIN"]
# Java AiReplyType @JsonValue
ReplyType = Literal["ANSWER", "CLARIFY", "REFUSE"]
# Java AiRefusalReason @JsonValue（7 值）
RefusalReason = Literal[
    "NO_RELIABLE_KNOWLEDGE", "LOW_CONFIDENCE", "CONFLICTING_KNOWLEDGE",
    "HIGH_RISK_TOPIC", "MODEL_UNAVAILABLE", "POLICY_BLOCKED", "OFF_TOPIC",
]


class RetrievalRequest(BaseModel):
    """对齐 Java RagRetrievalRequest（question 必填 ≤8000；categoryId ≤64；topK 1..20）。"""

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(min_length=1, max_length=8000)
    category_id: Optional[str] = Field(default=None, alias="categoryId", max_length=64)
    top_k: int = Field(default=5, alias="topK", ge=1, le=20)


class RetrievedChunk(BaseModel):
    """对齐 Java RetrievedChunk（consultation 侧要求 chunkId/.../content 均非空白）。"""

    model_config = ConfigDict(populate_by_name=True)

    chunk_id: str = Field(alias="chunkId")
    article_id: str = Field(alias="articleId")
    version_id: str = Field(alias="versionId")
    title: str
    snippet: str
    content: str
    category_id: Optional[str] = Field(default=None, alias="categoryId")
    score: float = Field(ge=0.0, le=1.0)
    index_version: str = Field(alias="indexVersion")


class RagRetrievalResponse(BaseModel):
    """对齐 Java RagRetrievalResponse（NON_NULL：null 字段序列化时省略）。"""

    model_config = ConfigDict(populate_by_name=True)

    items: List[RetrievedChunk]
    domain: Domain
    suggested_reply_type: ReplyType = Field(alias="suggestedReplyType")
    suggested_refusal_reason: Optional[RefusalReason] = Field(default=None, alias="suggestedRefusalReason")
    top_score: float = Field(alias="topScore", ge=0.0, le=1.0)
    reliable: bool
    published_only: bool = Field(alias="publishedOnly")


class ResultEnvelope(BaseModel):
    """对齐 Java com.itticket.common.api.Result（{code,msg,data}，code=0 成功，NON_NULL）。"""

    model_config = ConfigDict(populate_by_name=True)

    code: int
    msg: str
    data: Optional[object] = None

    @classmethod
    def ok(cls, data: object, msg: str = "success") -> "ResultEnvelope":
        return cls(code=0, msg=msg, data=data)

    @classmethod
    def err(cls, code: int, msg: str) -> "ResultEnvelope":
        return cls(code=code, msg=msg, data=None)


class HealthResponse(BaseModel):
    """服务自检回显：确认装配状态与在线预算是否已收紧。"""

    model_config = ConfigDict(populate_by_name=True)

    status: str                                   # UP | DEGRADED
    chunk_count: int = Field(alias="chunkCount")
    wiki_fingerprint: str = Field(alias="wikiFingerprint")
    config_fingerprint: str = Field(alias="configFingerprint")
    mapping_loaded: bool = Field(alias="mappingLoaded")
    mapping_entries: int = Field(alias="mappingEntries")
    query_rewrite: bool = Field(alias="queryRewrite")
    rewrite_timeout: float = Field(alias="rewriteTimeout")
    serialize_search: bool = Field(alias="serializeSearch")
    lock_wait_seconds: float = Field(alias="lockWaitSeconds")
    rerank_wait_budget: float = Field(alias="rerankWaitBudget")
    rerank_max_retries: int = Field(alias="rerankMaxRetries")
    rerank_request_timeout: float = Field(alias="rerankRequestTimeout")
    rerank_available: bool = Field(alias="rerankAvailable")
    rerank_provider: str = Field(alias="rerankProvider")
    rerank_degraded_count: int = Field(alias="rerankDegradedCount")   # 网关限流降级累计次数
