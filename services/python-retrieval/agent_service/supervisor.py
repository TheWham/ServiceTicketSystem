# -*- coding: utf-8 -*-
"""Supervisor 主管调度中心与 Guardrails 编排节点。

包含：
1. input_guard_node: 注入拦截 + PII 双向脱敏
2. supervisor_router_node: 自适应意图调度（知识子图 / 工单子图 / 终审）
3. formulator_node: 汇总各子图事实证据，严格组装 6 键结构化响应契约
4. output_guard_node: 敏感信息出网前于本地 Vault 中动态还原
"""

import json
import logging
import operator
import re
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.runnables import RunnableConfig

from .guardrails import GuardrailsSecurityEngine
from .model_client import ModelClient, ModelTurn

log = logging.getLogger(__name__)


class SupervisorTeamState(TypedDict):
    """Supervisor 主从协同全局状态模式。"""
    question: str
    sanitized_question: str
    pii_vault: Dict[str, str]
    security_flag: bool
    security_message: str
    next_action: str             # "CALL_KNOWLEDGE", "CALL_TICKET", "FINISH"
    knowledge_evidence: Optional[str]
    used_version_ids: List[str]
    ticket_evidence: Optional[str]
    ticket_draft: Optional[Dict[str, Any]]
    final_content: Optional[str] # 严格 6 键 JSON
    audit_trail: Annotated[List[str], operator.add]


def input_guard_node(state: SupervisorTeamState) -> Dict[str, Any]:
    """步骤 1：输入安全与合规护栏（Prompt 越狱注入拦截 + PII 掩码）。"""
    raw_query = state.get("question", "")
    is_safe, msg = GuardrailsSecurityEngine.check_prompt_injection(raw_query)

    if not is_safe:
        # 短路拒绝：0 Token 消耗，直接拦截
        refuse_payload = {
            "replyType": "REFUSE",
            "answerText": f"❌ 请求被安全护栏强行阻断：{msg}",
            "usedVersionIds": [],
            "confidence": 0.0,
            "knowledgeConflict": False,
            "offTopic": True
        }
        return {
            "security_flag": False,
            "security_message": msg,
            "next_action": "FINISH",
            "final_content": json.dumps(refuse_payload, ensure_ascii=False),
            "audit_trail": [f"【安全护栏】{msg}"]
        }

    sanitized_text, pii_map = GuardrailsSecurityEngine.mask_pii_data(raw_query)
    logs = ["【安全护栏】输入合规校验通过"]
    if pii_map:
        logs.append(f"【安全护栏】完成敏感信息脱敏，已掩码 {len(pii_map)} 项隐私数据至会话 Vault")

    return {
        "security_flag": True,
        "security_message": "合规",
        "sanitized_question": sanitized_text,
        "pii_vault": pii_map,
        "audit_trail": logs
    }


def supervisor_router_node(state: SupervisorTeamState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """步骤 2：Supervisor 主管决策中心（自适应任务委派与流向控制）。"""
    if not state.get("security_flag", True):
        return {"next_action": "FINISH", "audit_trail": ["【Supervisor】检测到安全拦截标志，直接结束流水线"]}

    question = state.get("sanitized_question") or state.get("question", "")
    has_knowledge = state.get("knowledge_evidence") is not None
    has_ticket = state.get("ticket_evidence") is not None

    # 意图特征识别
    ticket_keywords = [r"工单", r"查单", r"进度", r"建单", r"报修", r"处理了吗", r"申请"]
    needs_ticket_intent = any(re.search(kw, question) for kw in ticket_keywords)

    knowledge_keywords = [r"怎么", r"如何", r"办法", r"解决", r"失败", r"错误", r"代码", r"连不上", r"无法", r"蓝屏", r"网络", r"vpn", r"密码"]
    needs_knowledge_intent = any(re.search(kw, question, re.IGNORECASE) for kw in knowledge_keywords)

    # 默认：如果没有任何明确工单特征，优先按知识排障处理
    if not needs_ticket_intent and not needs_knowledge_intent:
        needs_knowledge_intent = True

    # 决策分派
    if needs_knowledge_intent and not has_knowledge:
        return {
            "next_action": "CALL_KNOWLEDGE",
            "audit_trail": ["【Supervisor 决策】委派任务给 -> [KnowledgeWorker 知识排障专家]"]
        }

    if needs_ticket_intent and not has_ticket:
        return {
            "next_action": "CALL_TICKET",
            "audit_trail": ["【Supervisor 决策】委派任务给 -> [TicketWorker 工单流转专家]"]
        }

    return {
        "next_action": "FINISH",
        "audit_trail": ["【Supervisor 决策】所需事实证据已全部就绪，进入终审汇编"]
    }


def formulator_node(state: SupervisorTeamState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """步骤 3：决策汇总与最终 6 键结构化 JSON 拼装。"""
    if not state.get("security_flag", True):
        # 已经准备了拒答包
        return {"audit_trail": ["【终审结案】单据安全违规，保留拒答结果"]}

    k_evidence = state.get("knowledge_evidence") or ""
    t_evidence = state.get("ticket_evidence") or ""
    used_versions = state.get("used_version_ids") or []
    draft = state.get("ticket_draft")

    answer_parts = []
    if k_evidence:
        answer_parts.append(k_evidence.strip())
    if t_evidence:
        answer_parts.append(t_evidence.strip())

    if not answer_parts:
        final_answer = "已为您处理完成当前咨询。"
    else:
        final_answer = "\n\n".join(answer_parts)

    response_payload = {
        "replyType": "ANSWER",
        "answerText": final_answer,
        "usedVersionIds": used_versions,
        "confidence": 0.95,
        "knowledgeConflict": False,
        "offTopic": False
    }

    return {
        "final_content": json.dumps(response_payload, ensure_ascii=False),
        "audit_trail": ["【终审结案】完成多源 Subagent 事实证据汇编，生成标准 6 键 JSON"]
    }


def output_guard_node(state: SupervisorTeamState) -> Dict[str, Any]:
    """步骤 4：输出安全还原护栏（在出网前无损还原 PII）。"""
    pii_vault = state.get("pii_vault") or {}
    raw_final = state.get("final_content") or "{}"
    draft = state.get("ticket_draft")

    # 还原 final_content 中的占位符
    safe_final = GuardrailsSecurityEngine.unmask_pii_data(raw_final, pii_vault)

    # 还原 ticket_draft 中的占位符
    safe_draft = None
    if draft:
        safe_draft = dict(draft)
        if "title" in safe_draft:
            safe_draft["title"] = GuardrailsSecurityEngine.unmask_pii_data(safe_draft["title"], pii_vault)
        if "description" in safe_draft:
            safe_draft["description"] = GuardrailsSecurityEngine.unmask_pii_data(safe_draft["description"], pii_vault)

    return {
        "final_content": safe_final,
        "ticket_draft": safe_draft,
        "audit_trail": ["【安全护栏】完成出网数据还原，敏感信息已精准解密"]
    }
