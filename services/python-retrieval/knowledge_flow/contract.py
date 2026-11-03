# services/python-retrieval/knowledge_flow/contract.py
"""知识库沉淀 LangGraph 流程编排数据契约与 DTO 定义。"""

import operator
from typing import TypedDict, Annotated, Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ==============================================================================
# 1. LangGraph State 结构契约 (TypedDict)
# ==============================================================================

class KnowledgeFlowState(TypedDict):
    """知识库沉淀全流程的核心状态对象。"""
    candidate_id: str                          # 候选案例唯一 ID（如 fb-xxx, tk-xxx）
    source_type: str                           # 来源类型：'AI_FEEDBACK' 或 'TICKET_RESOLUTION'
    raw_question: str                          # 原始员工提问或工单标题
    raw_answer: str                            # 原始回答正文或工程师排障解决记录
    
    # Node 1 产出：结构化提炼
    title: str                                 # 提炼后的标准知识标题
    summary: str                               # 核心摘要
    problem_desc: str                          # 结构化问题现象
    resolution_steps: str                      # 详细排查步骤
    category_id: str                           # 分类代码：C_NET, C_SW, C_HW, C_ACC, C_OTH
    risk_level: str                            # 'NORMAL' 或 'HIGH' (涉及账号/权限/安全为 HIGH)
    
    # Node 2 产出：脱敏与合规拦截
    is_sanitized: bool                         # 是否已完成脱敏
    contains_injection: bool                   # 是否包含 Prompt 注入攻击特征
    sanitized_question: str                    # 脱敏后问题
    sanitized_answer: str                      # 脱敏后答案/解决步骤
    
    # Node 3 产出：向量查重与聚类
    top_similarity_score: float                # 现有 Python 知识库中最相似向量的余弦得分
    is_duplicate: bool                         # 是否判定为疑似重复/已存在条目
    duplicate_reference: Optional[str]          # 命中的重复/相似知识标题与ID
    
    # Node 4 产出：人工审批 (HITL interrupt)
    review_status: str                         # 'PENDING_REVIEW', 'APPROVED', 'REJECTED'
    reviewer: Optional[str]                    # 审批人工号或姓名
    audit_comment: Optional[str]               # 审批附言或驳回原因
    
    # Node 5 产出：Python 向量库入库与版本
    published_version_id: Optional[str]        # 正式发布的版本 ID（如 ver-20261102-xxx）
    indexed_chunk_count: int                   # 写入 Python Chroma/Docstore 的切片数量
    
    # Reducer: 审计跟踪全流程日志列表（自动追加累加）
    audit_logs: Annotated[List[str], operator.add]


# ==============================================================================
# 2. RESTful API 请求与响应 DTO (Pydantic Models)
# ==============================================================================

class TriggerFlowRequest(BaseModel):
    """发起知识沉淀编排请求。"""
    candidate_id: Optional[str] = Field(None, description="候选案例ID，留空自动生成")
    source_type: str = Field("AI_FEEDBACK", description="来源类型：AI_FEEDBACK / TICKET_RESOLUTION")
    question: str = Field(..., description="原始提问或故障标题")
    answer: str = Field(..., description="原始解决方案正文")
    category_hint: Optional[str] = Field(None, description="分类提示（可选）")


class KnowledgeReviewDecision(BaseModel):
    """外部管理员对中断挂起任务给出的审核裁决。"""
    action: str = Field(..., description="决议：APPROVED (通过并发布) 或 REJECTED (驳回)")
    approver: str = Field(..., description="审批人姓名或工号")
    comment: Optional[str] = Field(None, description="审批意见或驳回原因")
    modified_title: Optional[str] = Field(None, description="审批人订正后的标题（可选）")
    modified_steps: Optional[str] = Field(None, description="审批人订正后的解决步骤（可选）")


class TimeTravelPatchRequest(BaseModel):
    """Time-Travel 历史快照热修补请求。"""
    checkpoint_id: str = Field(..., description="需要注入修补补丁的目标快照 ID")
    patch_values: Dict[str, Any] = Field(..., description="需要订正的字段键值字典（如修改 category_id, resolution_steps）")


class FlowResponse(BaseModel):
    """统一流程响应体。"""
    code: int = 0
    message: str = "success"
    thread_id: str
    status: str
    is_paused: bool = False
    current_node: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    interrupt_payload: Optional[Dict[str, Any]] = None
