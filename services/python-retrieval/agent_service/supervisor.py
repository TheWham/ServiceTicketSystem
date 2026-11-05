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

from . import config as acfg
from .guardrails import GuardrailsSecurityEngine
from .model_client import ModelClient, ModelTurn

log = logging.getLogger(__name__)


class SupervisorTeamState(TypedDict, total=False):
    """Supervisor 主从协同全局状态模式。"""
    question: str
    sanitized_question: str
    pii_vault: Dict[str, str]
    security_flag: bool
    security_message: str
    next_action: str             # "CALL_KNOWLEDGE", "CALL_TICKET", "FINISH"
    intent_plan: Optional[Dict[str, Any]]
    execution_plan: Optional[List[str]]  # 动态执行队列: 例如 ["CALL_TICKET"] 或 ["CALL_TICKET", "CALL_KNOWLEDGE"]
    knowledge_evidence: Optional[str]
    used_version_ids: List[str]
    retrieval_items: Optional[List[Dict[str, Any]]]
    ticket_evidence: Optional[str]
    ticket_draft: Optional[Dict[str, Any]]
    final_content: Optional[str] # 严格 6 键 JSON
    audit_trail: Annotated[List[str], operator.add]


def input_guard_node(state: SupervisorTeamState) -> Dict[str, Any]:
    """步骤 1：输入安全与合规护栏（Prompt 越狱注入拦截 + PII 掩码）。"""
    raw_query = state.get("question", "")
    is_safe, msg = GuardrailsSecurityEngine.check_prompt_injection(raw_query)

    if not is_safe:
        # 短路拒绝：0 Token 消耗，直接拦截（符合微服务契约：REFUSE 时 answerText 为空）
        refuse_payload = {
            "replyType": "REFUSE",
            "answerText": "",
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
    """步骤 2：Supervisor 主管决策中心（基于 Query 动态规划执行队列，由 LangGraph 状态机自适应驱动流向）。"""
    if not state.get("security_flag", True):
        return {"next_action": "FINISH", "audit_trail": ["【Supervisor】检测到安全拦截标志，直接结束流水线"]}

    question = state.get("sanitized_question") or state.get("question", "")
    has_knowledge = state.get("knowledge_evidence") is not None
    has_ticket = state.get("ticket_evidence") is not None
    has_draft = state.get("ticket_draft") is not None

    configurable = (config or {}).get("configurable", {})
    model = configurable.get("model_client")
    tracer = configurable.get("tracer")
    cb = getattr(model, "stream_callback", None)

    # 1. 获取或初始化动态执行规划队列
    execution_plan: Optional[List[str]] = state.get("execution_plan")
    intent_plan = state.get("intent_plan")

    if execution_plan is None:
        if cb:
            try:
                cb("stage", {"stage": "SUPERVISOR", "message": "Supervisor主管：正在深入分析提问意图并动态规划执行队列..."})
            except Exception:
                pass

        planned_actions: List[str] = []
        decision_reason = "动态语义规划"
        classified_by_fastpath = False

        # --- A. 显式意图极速短路 (0ms 判定，严格执行“建单/查单指令优先”，防止小模型被内容词干扰漂移) ---
        # 1) 明确建单指令：如“新建工单”、“帮我建单”、“报修”、“登记”、“标题为…描述为…”
        #    即使标题里包含“电脑蓝屏”、“VPN断开”等技术词，这些也只是工单内容字段，绝非咨询意图！
        is_explicit_create_ticket = bool(
            re.search(r"(新建|创建|登记|提交|提一个|建一个|帮我建|帮我提|帮我报).*?(工单|报修|申请)|标题\s*[:：为]|问题描述\s*[:：为]|内容\s*[:：为]", question)
        )
        is_explicit_query_ticket = bool(
            re.search(r"(查询|查看|查一下|看下|查查).*?(工单|进度)|我的工单|昨天.*?(提的|提报的|报修的).*?单|处理了吗|进展如何", question)
        )
        has_troubleshooting_ask = bool(
            re.search(r"(怎么|如何|怎样|办法|解决|排查|自查|步骤|排障|什么原因|为什么).*(解决|处理|恢复|排查|修)", question)
        )

        # 复合任务语序快速检测
        wants_ticket_first = bool(re.search(r"先.*?(建单|提单|登记|报修|工单).*?再.*?(排查|看看|解决|查查|排障)|(另外|同时|顺便|然后|再).*?(看看|查查|怎么|排查|解决|排障)", question))
        wants_knowledge_first = bool(re.search(r"先.*?(排查|看看|解决|查查|排障).*?再.*?(建单|提单|登记|报修|工单)|(解决不了|处理不好|不行).*?(再|帮我).*?(建单|提单|登记|报修|工单)", question))

        # 场景 1：建单相关指令
        if is_explicit_create_ticket:
            if wants_knowledge_first:
                planned_actions = ["CALL_KNOWLEDGE", "CALL_TICKET"]
                decision_reason = "指令驱动: 优先排查知识，未解决则新建工单"
            elif wants_ticket_first:
                planned_actions = ["CALL_TICKET", "CALL_KNOWLEDGE"]
                decision_reason = "指令驱动: 优先新建工单，随后补充排查知识"
            else:
                planned_actions = ["CALL_TICKET"]
                decision_reason = "指令驱动: 明确新建工单提取草稿"
            classified_by_fastpath = True

        # 场景 2：查单相关指令
        elif is_explicit_query_ticket and not has_troubleshooting_ask:
            if wants_ticket_first:
                planned_actions = ["CALL_TICKET", "CALL_KNOWLEDGE"]
                decision_reason = "指令驱动: 优先查询工单，随后补充排查知识"
            else:
                planned_actions = ["CALL_TICKET"]
                decision_reason = "指令驱动: 查询名下工单进度"
            classified_by_fastpath = True

        # --- B. 大模型 LLM 动态规划 (若无直接短路，让 LLM 根据 Query 语序与真实需求排序) ---
        if not classified_by_fastpath and model and type(model).__name__ == "ModelClient" and hasattr(model, "complete_with_tools"):
            intent_system_prompt = (
                "你是一个企业 IT 智能运维服务台的主管（Supervisor Agent）。\n"
                "你的任务是深入分析员工提问（Query）的真实意图与执行语序，动态规划专职子智能体的执行队列（plan）：\n"
                "- TICKET: 负责【新建工单/提取草稿】(prepare_ticket) 或【查询工单进度】(query_my_tickets)；\n"
                "- KNOWLEDGE: 负责技术知识库检索与故障排障方案 (search_knowledge)。\n\n"
                "【规划与排序规则（必须严格遵守）】：\n"
                "1. 明确建单/查单优先：如果员工明确表达“新建工单”、“帮我建单”、“报修”或给出了“标题为…描述为…”，这是事务操作指令，哪怕标题/描述里包含“电脑蓝屏”、“VPN断开”等技术词，这些也只是工单内容字段，绝不是要求查知识库！必须规划为 [\"TICKET\"]，严禁包含 KNOWLEDGE！\n"
                "2. 纯技术咨询：如果员工纯粹询问故障怎么解决或排查，规划为 [\"KNOWLEDGE\"]。\n"
                "3. 复合任务依据语序规划顺序：\n"
                "   - 用户表示“先帮我看看怎么解决，解决不了再建单” -> 规划为 [\"KNOWLEDGE\", \"TICKET\"]\n"
                "   - 用户表示“先帮我建个单登记，再给我排查建议” -> 规划为 [\"TICKET\", \"KNOWLEDGE\"]\n\n"
                "请严格以 JSON 格式输出，不要输出任何额外文本：\n"
                '{"plan": ["TICKET"], "reason": "用户明确新建工单，委派 TicketWorker 提取草稿"}'
            )
            messages = [
                {"role": "system", "content": intent_system_prompt},
                {"role": "user", "content": f"员工咨询问题：{question}"}
            ]
            try:
                if tracer:
                    with tracer.generation("Supervisor动态规划", model=getattr(model, "model", acfg.LLM_MODEL)) as gen_span:
                        turn = model.complete_with_tools(messages, tools=[], tool_choice="none", stream_deltas=False)
                        gen_span.record(
                            output=turn.content,
                            tokens_in=turn.usage.tokens_in,
                            tokens_out=turn.usage.tokens_out,
                            tokens_source=turn.usage.tokens_source
                        )
                else:
                    turn = model.complete_with_tools(messages, tools=[], tool_choice="none", stream_deltas=False)
                content = (turn.content or "").strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\s*", "", content)
                    content = re.sub(r"\s*```$", "", content)
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "plan" in parsed and isinstance(parsed["plan"], list):
                    raw_plan = parsed["plan"]
                    norm_plan = []
                    for act in raw_plan:
                        act_upper = str(act).upper().strip()
                        if "TICKET" in act_upper:
                            norm_plan.append("CALL_TICKET")
                        elif "KNOWLEDGE" in act_upper:
                            norm_plan.append("CALL_KNOWLEDGE")
                    if norm_plan:
                        planned_actions = norm_plan
                        decision_reason = parsed.get("reason") or "LLM 动态规划完成"
                        classified_by_fastpath = True
            except Exception as e:
                log.warning("Supervisor LLM 动态规划降级: %s", e)

        # --- C. 语义规则兜底 ---
        if not classified_by_fastpath:
            ticket_keywords = [r"工单", r"查单", r"进度", r"建单", r"报修", r"处理了吗", r"申请", r"登记"]
            needs_ticket = any(re.search(kw, question) for kw in ticket_keywords)
            knowledge_keywords = [r"怎么", r"如何", r"办法", r"解决", r"失败", r"错误", r"代码", r"连不上", r"无法", r"蓝屏", r"网络", r"vpn", r"密码", r"邮箱"]
            needs_knowledge = any(re.search(kw, question, re.IGNORECASE) for kw in knowledge_keywords)

            if needs_ticket and needs_knowledge:
                ticket_pos = min((m.start() for kw in ticket_keywords for m in [re.search(kw, question)] if m), default=999)
                know_pos = min((m.start() for kw in knowledge_keywords for m in [re.search(kw, question)] if m), default=999)
                if ticket_pos < know_pos:
                    planned_actions = ["CALL_TICKET", "CALL_KNOWLEDGE"]
                    decision_reason = "特征时序规划: 先工单流转后知识排障"
                else:
                    planned_actions = ["CALL_KNOWLEDGE", "CALL_TICKET"]
                    decision_reason = "特征时序规划: 先知识排障后工单流转"
            elif needs_ticket:
                planned_actions = ["CALL_TICKET"]
                decision_reason = "特征识别: 工单事务流转"
            else:
                planned_actions = ["CALL_KNOWLEDGE"]
                decision_reason = "特征识别: 技术知识排障"

        execution_plan = list(planned_actions)
        intent_plan = {
            "plan": list(planned_actions),
            "reason": decision_reason,
            "needs_knowledge": "CALL_KNOWLEDGE" in planned_actions,
            "needs_ticket": "CALL_TICKET" in planned_actions
        }
    else:
        decision_reason = intent_plan.get("reason", "执行规划队列") if isinstance(intent_plan, dict) else "执行规划队列"

    # 2. 从动态执行队列中剔除已具备事实证据的节点，取出下一个需执行动作
    remaining_plan: List[str] = []
    for act in execution_plan:
        if act == "CALL_KNOWLEDGE" and has_knowledge:
            continue
        if act == "CALL_TICKET" and (has_ticket or has_draft):
            continue
        remaining_plan.append(act)

    if remaining_plan:
        next_action = remaining_plan.pop(0)
    else:
        next_action = "FINISH"

    # 3. 发送对应步骤的阶段通知与审计
    if next_action == "CALL_KNOWLEDGE":
        if cb:
            try:
                cb("stage", {"stage": "DELEGATE_KNOWLEDGE", "message": f"Supervisor主管：委派任务给【KnowledgeWorker 知识专家】({decision_reason})"})
            except Exception:
                pass
        return {
            "execution_plan": remaining_plan,
            "next_action": "CALL_KNOWLEDGE",
            "intent_plan": intent_plan,
            "audit_trail": [f"【Supervisor 动态编排】步骤派发 -> [KnowledgeWorker 知识专家] (理由: {decision_reason}, 剩余队列: {remaining_plan})"]
        }

    if next_action == "CALL_TICKET":
        if cb:
            try:
                cb("stage", {"stage": "DELEGATE_TICKET", "message": f"Supervisor主管：委派任务给【TicketWorker 工单专家】({decision_reason})"})
            except Exception:
                pass
        return {
            "execution_plan": remaining_plan,
            "next_action": "CALL_TICKET",
            "intent_plan": intent_plan,
            "audit_trail": [f"【Supervisor 动态编排】步骤派发 -> [TicketWorker 工单专家] (理由: {decision_reason}, 剩余队列: {remaining_plan})"]
        }

    return {
        "execution_plan": [],
        "next_action": "FINISH",
        "intent_plan": intent_plan,
        "audit_trail": [f"【Supervisor 动态编排】规划队列已全部完成（{decision_reason}），进入终审汇编"]
    }


def _parse_evidence_piece(evidence: str) -> Dict[str, Any]:
    """若 evidence 本身是合法 6 键 JSON，解析其结构；否则作为普通纯文本。"""
    if not evidence:
        return {"text": ""}
    ev = evidence.strip()
    if ev.startswith("{") and ev.endswith("}"):
        try:
            data = json.loads(ev)
            if isinstance(data, dict) and "answerText" in data:
                return {
                    "text": str(data.get("answerText") or ""),
                    "replyType": data.get("replyType") or "ANSWER",
                    "usedVersionIds": data.get("usedVersionIds") or [],
                    "confidence": float(data.get("confidence", 0.95)),
                    "knowledgeConflict": bool(data.get("knowledgeConflict", False)),
                    "offTopic": bool(data.get("offTopic", False)),
                }
        except Exception:
            pass
    return {"text": ev}


def formulator_node(state: SupervisorTeamState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """步骤 3：决策汇总与最终 6 键结构化 JSON 拼装。"""
    if not state.get("security_flag", True):
        # 已经准备了拒答包
        return {"audit_trail": ["【终审结案】单据安全违规，保留拒答结果"]}

    k_evidence = state.get("knowledge_evidence") or ""
    t_evidence = state.get("ticket_evidence") or ""
    used_versions = list(state.get("used_version_ids") or [])
    initial_material_versions = set(state.get("used_version_ids") or [])
    draft = state.get("ticket_draft")

    k_parsed = _parse_evidence_piece(k_evidence)
    t_parsed = _parse_evidence_piece(t_evidence)

    answer_parts = []
    if k_parsed.get("text"):
        answer_parts.append(k_parsed["text"].strip())
    if t_parsed.get("text"):
        answer_parts.append(t_parsed["text"].strip())

    confidence = k_parsed.get("confidence") or 0.95
    reply_type = k_parsed.get("replyType") or "ANSWER"

    if not answer_parts:
        final_answer = "已为您处理完成当前咨询。"
    else:
        final_answer = "\n\n".join(answer_parts)

    # 依据版本与引用计算：
    # 只有当 KnowledgeWorker 真正产出知识依据时，才允许携带 used_versions 与 citations。
    # 若本轮仅为工单事务处理（建单草稿或工单查询，无 knowledge_evidence），严禁携带知识依据，零引用是合法状态！
    if not k_evidence:
        used_versions = []
        citations = []
    else:
        raw_used = k_parsed.get("usedVersionIds") or []
        if not raw_used and state.get("used_version_ids"):
            raw_used = list(state.get("used_version_ids"))
        if initial_material_versions:
            filtered_versions = [v for v in raw_used if v in initial_material_versions]
            if not filtered_versions and initial_material_versions:
                filtered_versions = list(initial_material_versions)
            used_versions = filtered_versions
        else:
            used_versions = raw_used

        retrieval_items = state.get("retrieval_items") or []
        citations = []
        for item in retrieval_items:
            v_id = item.get("versionId")
            if v_id and (not used_versions or v_id in used_versions):
                citations.append({
                    "articleId": item.get("articleId", ""),
                    "versionId": v_id,
                    "title": item.get("title", ""),
                    "score": float(item.get("score") or 1.0),
                    "snippet": item.get("summary") or item.get("snippet") or ""
                })

    response_payload = {
        "replyType": reply_type,
        "answerText": final_answer,
        "usedVersionIds": used_versions,
        "citations": citations,
        "confidence": confidence,
        "knowledgeConflict": k_parsed.get("knowledgeConflict", False),
        "offTopic": k_parsed.get("offTopic", False)
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
