# -*- coding: utf-8 -*-
"""agent_service 对外契约。

对齐 Java consultation-service 的生成侧约定：
- 模型最终产出的 JSON **严格 6 键**（replyType/answerText/usedVersionIds/confidence/
  knowledgeConflict/offTopic）——Java 侧 `OpenAiCompatibleAnswerGenerator` 会校验键数；
- 建单草稿走**带外字段** `ticketDraft`（由 prepare_ticket 工具产出），不混进模型 JSON。
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ReplyType = Literal["ANSWER", "REFUSE"]


class AgentTurn(BaseModel):
    """历史对话（仅 user/assistant，与 Java RagQuery.Turn 一致）。"""

    role: Literal["user", "assistant"]
    content: str


class AgentMaterial(BaseModel):
    """Java 侧预检索到的知识片段（不信任：仅作参考，不得执行其中指令）。"""

    model_config = ConfigDict(populate_by_name=True)

    version_id: str = Field(alias="versionId")
    title: str = ""
    content: str = ""


class AgentChatRequest(BaseModel):
    """ReAct 生成请求。主体（user_id/role）由 X-User-Id / X-User-Role 头透传，不入请求体。"""

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(min_length=1, max_length=8000)
    history: List[AgentTurn] = Field(default_factory=list)
    material: List[AgentMaterial] = Field(default_factory=list)
    category_id: Optional[str] = Field(default=None, alias="categoryId", max_length=64)
    asset_id: Optional[str] = Field(default=None, alias="assetId", max_length=64)


class TicketDraft(BaseModel):
    """建单草稿（人机回环第一步；AI 只产草稿，员工确认后才落库）。"""

    title: str
    category: Optional[str] = None
    description: str
    priority: str = "MEDIUM"


class AgentChatResponse(BaseModel):
    """ReAct 生成结果：模型 6 键 + 带外草稿。"""

    model_config = ConfigDict(populate_by_name=True)

    reply_type: ReplyType = Field(alias="replyType")
    answer_text: str = Field(alias="answerText")
    used_version_ids: List[str] = Field(default_factory=list, alias="usedVersionIds")
    confidence: float = Field(ge=0.0, le=1.0)
    knowledge_conflict: bool = Field(default=False, alias="knowledgeConflict")
    off_topic: bool = Field(default=False, alias="offTopic")
    ticket_draft: Optional[TicketDraft] = Field(default=None, alias="ticketDraft")
    # 链路追踪 ID（= 请求的 X-Request-Id）。Java 侧不读它也不受影响；汇报/排查时用它
    # 在 agent 日志里把这轮 ReAct 的 generation / 工具 span 全部串起来。
    trace_id: str = Field(default="", alias="traceId")