# -*- coding: utf-8 -*-
"""垂直领域子智能体：KnowledgeSubagent (知识排障专家)。

职责单一，专注 IT 知识库检索、多跳事实查验与技术故障排障指导。
只挂载 search_knowledge 白名单工具，提示词精简专业，消除提示词污染。
"""

import json
import logging
import operator
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from ..model_client import ModelClient, ModelTurn
from ..tools import ToolContext, dispatch, tool_specs

log = logging.getLogger(__name__)


class KnowledgeSubagentState(TypedDict):
    """知识排障子图局部状态契约。"""
    question: str
    messages: Annotated[List[Dict[str, Any]], operator.add]
    step: int
    max_steps: int
    latest_tool_calls: List[Dict[str, Any]]
    knowledge_evidence: Optional[str]
    used_version_ids: List[str]
    audit_trail: Annotated[List[str], operator.add]


def _knowledge_system_prompt() -> str:
    return """你是一位精通企业 IT 办公技术排障的资深工程师（知识专家）。
你的职责是：
1. 深入分析员工的故障症状，调用 search_knowledge 工具从企业知识库中检索官方排障指引；
2. 如果存在关联原因，仔细比对排障步骤与注意要点；
3. 输出清晰、专业、分步骤的技术解决方案，直接陈述排查与解决要点，不要输出废话；
4. 严格禁止索要用户密码或提供高风险系统破坏命令。"""


def knowledge_model_node(state: KnowledgeSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """知识专家决策节点。"""
    configurable = (config or {}).get("configurable", {})
    model: ModelClient = configurable.get("model_client")
    step = state.get("step", 0)
    max_steps = state.get("max_steps", 3)
    messages = state.get("messages", [])

    # 只挂载 search_knowledge 工具规范
    specs = [s for s in tool_specs() if s.get("function", {}).get("name") == "search_knowledge"]
    last_step = (step >= max_steps - 1)
    tool_choice = "none" if last_step else "auto"

    # 若尚未挂载专职系统提示词，前置注入
    full_messages = messages
    if not any(m.get("role") == "system" for m in messages):
        full_messages = [{"role": "system", "content": _knowledge_system_prompt()}] + messages

    turn: ModelTurn = model.complete_with_tools(full_messages, specs, tool_choice)

    if not turn.has_tool_calls:
        # 模型已完成推理，得出最终排障依据
        evidence = turn.content or "已完成知识库排障检索"
        return {
            "step": step + 1,
            "latest_tool_calls": [],
            "knowledge_evidence": evidence,
            "audit_trail": [f"【KnowledgeWorker】完成排障推理，输出解决方案要点"]
        }

    tool_calls_dict = [
        {"id": c.id, "name": c.name, "arguments": c.arguments}
        for c in turn.tool_calls
    ]
    assistant_msg = {
        "role": "assistant",
        "content": turn.content or "",
        "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)}}
            for c in turn.tool_calls
        ]
    }
    return {
        "step": step + 1,
        "messages": [assistant_msg],
        "latest_tool_calls": tool_calls_dict,
        "audit_trail": [f"【KnowledgeWorker】第 {step + 1} 轮决策调工具: {[c.name for c in turn.tool_calls]}"]
    }


def knowledge_tool_node(state: KnowledgeSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """知识专家工具执行节点。"""
    configurable = (config or {}).get("configurable", {})
    ctx: ToolContext = configurable.get("ctx")
    tool_calls = state.get("latest_tool_calls", [])

    tool_messages: List[Dict[str, Any]] = []
    audit_logs: List[str] = []

    for call in tool_calls:
        call_id = call.get("id")
        name = call.get("name")
        args = call.get("arguments", {})

        # 执行工具
        result = dispatch(name, args, ctx)
        tool_messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": json.dumps(result, ensure_ascii=False)
        })
        audit_logs.append(f"【KnowledgeWorker】执行工具 {name} 完成 (成功={result.get('success', False)})")

    return {
        "messages": tool_messages,
        "latest_tool_calls": [],
        "audit_trail": audit_logs
    }


def should_continue(state: KnowledgeSubagentState) -> str:
    calls = state.get("latest_tool_calls") or []
    if calls:
        if state.get("step", 0) >= state.get("max_steps", 3):
            return END
        return "knowledge_tool_node"
    return END


def build_knowledge_subagent(checkpointer: Optional[BaseCheckpointSaver] = None):
    """编译独立的 KnowledgeWorker LangGraph 子状态图。"""
    workflow = StateGraph(KnowledgeSubagentState)
    workflow.add_node("knowledge_model_node", knowledge_model_node)
    workflow.add_node("knowledge_tool_node", knowledge_tool_node)

    workflow.add_edge(START, "knowledge_model_node")
    workflow.add_conditional_edges("knowledge_model_node", should_continue, {
        "knowledge_tool_node": "knowledge_tool_node",
        END: END
    })
    workflow.add_edge("knowledge_tool_node", "knowledge_model_node")

    return workflow.compile(checkpointer=checkpointer)
