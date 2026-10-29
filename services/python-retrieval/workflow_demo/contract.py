# -*- coding: utf-8 -*-
"""工作流契约：内部状态对象 + HTTP 请求模型。

对外字段刻意复用项目既有词汇（`ReplyType` / `RefusalReason` / `Result` 包络），
这样接入产品时 Java 侧无需为本 demo 新造一套枚举。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from rag_service.contract import ReplyType, RefusalReason  # noqa: F401  （对外复用，供调用方引用）

# ---------------------------------------------------------------- 意图（Node 1 产出）
INTENT_KNOWLEDGE = "KNOWLEDGE_QA"     # 知识问答
INTENT_MY_TICKETS = "MY_TICKETS"      # 查本人名下工单
INTENT_CREATE_TICKET = "CREATE_TICKET"  # 申请建单
INTENT_UNSUPPORTED = "UNSUPPORTED"    # 越界/与 IT 服务无关 → 短路拒答

INTENTS = (INTENT_KNOWLEDGE, INTENT_MY_TICKETS, INTENT_CREATE_TICKET, INTENT_UNSUPPORTED)

# ---------------------------------------------------------------- 裁决（Node 3 产出）
VERDICT_ANSWERED = "ANSWERED"        # 已回答（知识问答 / 工单查询）
VERDICT_DRAFT_READY = "DRAFT_READY"  # 门禁通过，产出建单草稿（仍需员工确认）
VERDICT_NEEDS_INFO = "NEEDS_INFO"    # 字段不足，回问员工
VERDICT_BLOCKED = "BLOCKED"          # 规则拦截（重复单 / 敏感操作）
VERDICT_REFUSED = "REFUSED"          # 越界拒答

# 裁决 → 项目既有 ReplyType 的映射（接入 Java 时直接可用）
VERDICT_TO_REPLY_TYPE: Dict[str, str] = {
    VERDICT_ANSWERED: "ANSWER",
    VERDICT_DRAFT_READY: "ANSWER",
    VERDICT_NEEDS_INFO: "CLARIFY",
    VERDICT_BLOCKED: "REFUSE",
    VERDICT_REFUSED: "REFUSE",
}


@dataclass
class KnowledgeItem:
    """一条已发布知识（只可能是 current_version_id 指向的版本）。"""

    article_id: str
    version_id: str
    version_no: int
    title: str
    summary: str
    body: str
    category_id: str
    score: float


@dataclass
class TicketSummary:
    ticket_id: str
    title: str
    category_id: str
    category_name: str
    status: str
    priority: str
    created_at: str
    assignee_id: Optional[str] = None


@dataclass
class TicketDraft:
    """建单草稿：**只产草稿、不落库**，等员工确认（对齐 agent_service 的人机回环）。"""

    title: str
    description: str
    category_id: Optional[str] = None
    priority: str = "MEDIUM"


@dataclass
class RuleFinding:
    """一条确定性规则的判定结果，作为审计依据随响应返回。"""

    code: str
    message: str
    severity: str = "INFO"  # INFO | BLOCK

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass
class WorkflowState:
    """在节点间递进的状态对象（Day17 模式 1：Prompt Chaining 的载体）。

    节点之间不互相调用，全靠这个对象衔接，所以**它就是这条链路的接线图**。
    下面每个字段都标了「谁写 / 谁读」—— 顺着这些标注读一遍，等于把整条链路走了一遍。
    """

    # ---- 入口注入（engine.run 的入参，此后只读）----
    question: str
    user_id: str
    role: str

    # ---- Node 1 写；engine 读（决定要不要短路）、Node 3 读（决定走哪套裁决）----
    intent: Optional[str] = None

    # ---- Node 2 写：并行扇出的左右两路各填一个 ----
    knowledge: List[KnowledgeItem] = field(default_factory=list)
    my_tickets: List[TicketSummary] = field(default_factory=list)

    # ---- Node 1/3 写（判定依据）；随响应回传给前端做审计展示 ----
    findings: List[RuleFinding] = field(default_factory=list)

    # ---- Node 3 写；Node 4 读（唯一的动作依据）、engine 读（收口时判空兜底）----
    verdict: Optional[str] = None
    refusal_reason: Optional[str] = None

    # ---- Node 3 写：建单路径上的裁决产物（查工单/知识问答路径不填）----
    category_id: Optional[str] = None
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    priority: Optional[str] = None
    sla: Dict[str, Any] = field(default_factory=dict)
    draft: Optional[TicketDraft] = None

    # ---- Node 3 写：终审文案，以及过了引用守卫、真正可引用的版本号 ----
    answer_text: str = ""
    used_version_ids: List[str] = field(default_factory=list)

    # ---- engine 写：节点异常时的降级记录（链路不中断，但要把失败留痕）----
    errors: List[str] = field(default_factory=list)

    def add_finding(self, code: str, message: str, severity: str = "INFO") -> None:
        self.findings.append(RuleFinding(code=code, message=message, severity=severity))


# ---------------------------------------------------------------- HTTP 契约

class WorkflowRunRequest(BaseModel):
    """运行一次工作流。`question` 与 `caseId` 二选一，都缺则 400。"""

    model_config = ConfigDict(populate_by_name=True)

    question: Optional[str] = Field(default=None, max_length=8000)
    case_id: Optional[str] = Field(default=None, alias="caseId", max_length=64)
    user_id: Optional[str] = Field(default=None, alias="userId", max_length=64)


class DemoCase(BaseModel):
    """演示用例：一句话 + 它会走到哪条路径，用于前端一键触发。"""

    model_config = ConfigDict(populate_by_name=True)

    case_id: str = Field(alias="caseId")
    label: str
    question: str
    expect: str          # 预期结论，用于对照「实际 vs 预期」
    highlights: List[str] = Field(default_factory=list)