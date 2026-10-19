# -*- coding: utf-8 -*-
"""day16 对外数据模型（Pydantic v2）。

分两类：
1. 工具入参契约（Fast-Fail 前置门禁）—— SafeText2SQLInput / SubmitEscalationInput，
   由宿主沙箱在派发物理工具前做硬校验，非法参数直接拦截不落地；
2. 对外 API 出参模型—— AgentChatRequest/AgentChatResponse/ToolStep/HealthResponse，
   供 FastAPI 演示页与 JSON 接口使用。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# 1. 工具入参严格契约（对齐讲义「Pydantic 严格模式」）
# ==============================================================================

class SafeText2SQLInput(BaseModel):
    """安全 Text2SQL 输入契约（强制思维链：先讲清业务意图，再给 SQL）。"""

    query_rationale: str = Field(..., description="生成该 SQL 的业务意图与推导逻辑（强制思维链）")
    generated_sql: str = Field(..., description="经过严格合规约束的只读 SELECT SQL 语句")


class SubmitEscalationInput(BaseModel):
    """外部协同系统「工单升级/加急」提交输入契约（正则 + 枚举硬约束）。"""

    ticket_id: str = Field(..., pattern=r"^TK\d+$",
                           description="工单号，必须为 TK 开头后接数字，如 TK202609300013")
    escalation_reason: str = Field(..., min_length=5,
                                   description="升级/加急原因，注明故障影响范围与依据")
    target_priority: Optional[str] = Field(default="HIGH",
                                           description="目标优先级：HIGH / MEDIUM / LOW")
    notes: Optional[str] = Field(default=None, description="备注")


# ==============================================================================
# 2. 对外 API 出参模型
# ==============================================================================

class ToolStep(BaseModel):
    """一次 ReAct 工具调用轨迹（供演示页可视化决策闭环）。"""

    step: int = Field(description="推理步序号")
    tool: str = Field(description="被调用的工具名，如 execute_safe_sql")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具入参")
    output: Dict[str, Any] = Field(default_factory=dict, description="工具执行反馈")
    success: bool = Field(default=False, description="该步是否执行成功（拦截/失败为 False）")


class AgentChatRequest(BaseModel):
    """Agent 问答入参。query 必填；max_steps 为自愈反思轮次上限。"""

    query: str = Field(min_length=1, max_length=8000)
    max_steps: Optional[int] = Field(default=5, ge=1, le=10)


class AgentChatResponse(BaseModel):
    """Agent 问答出参。

    mode — llm（真实 Function Calling）/ sandbox（确定性沙箱兜底，断网或未配 LLM）。
    trajectory — ReAct 完整工具调用轨迹（每步的工具名/入参/反馈/是否成功）。
    """

    query: str
    answer: str
    mode: str = "sandbox"          # llm | sandbox
    trajectory: List[ToolStep] = Field(default_factory=list)
    latency_ms: float = 0.0


class HealthResponse(BaseModel):
    """服务健康回显：LLM Function Calling 可用性 + 工具清单 + 是否强制沙箱。"""

    status: str = "UP"             # UP | DEGRADED（DEGRADED=LLM 不可用，走沙箱兜底）
    llm_available: bool = False
    llm_model: str = ""
    offline: bool = False
    tools: List[str] = Field(default_factory=list)
