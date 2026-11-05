# -*- coding: utf-8 -*-
"""垂直领域子智能体：TicketSubagent (工单事务专家)。

职责单一，专注查询员工个人工单流转现状与将故障事实提取为规范工单草稿。
只挂载 query_my_tickets 与 prepare_ticket 白名单工具，严格执行建单防误触红线（只产草稿、不落库）。
"""

import json
import logging
import operator
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from .. import config as acfg
from ..model_client import ModelClient, ModelTurn
from ..tools import ToolContext, dispatch, tool_specs

log = logging.getLogger(__name__)


class TicketSubagentState(TypedDict):
    """工单事务子图局部状态契约。"""
    question: str
    messages: Annotated[List[Dict[str, Any]], operator.add]
    step: int
    max_steps: int
    latest_tool_calls: List[Dict[str, Any]]
    ticket_evidence: Optional[str]
    ticket_draft: Optional[Dict[str, Any]]
    audit_trail: Annotated[List[str], operator.add]


def _ticket_system_prompt() -> str:
    return """你是一位企业 IT 服务台的工单事务助理。
你的职责是：
1. 若员工询问历史工单进度，调用 query_my_tickets 工具核查其名下真实工单状态与处理人；
2. 若员工遇到无法自助解决的技术故障要求建单，调用 prepare_ticket 整理规范工单草稿；
3. 重要红线：只能根据员工本轮明确陈述的事实提取标题和描述，不得虚构、不得代为决定。只产出草稿供员工在前端确认，严禁落库。
4. 完成处理后直接给出客观的工单状态说明或草稿提示，不要输出冗余信息。"""


def ticket_model_node(state: TicketSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """工单专家决策节点。"""
    configurable = (config or {}).get("configurable", {})
    model: ModelClient = configurable.get("model_client")
    step = state.get("step", 0)
    max_steps = state.get("max_steps", 3)
    messages = state.get("messages", [])

    # 只挂载 query_my_tickets 和 prepare_ticket
    allowed_tools = {"query_my_tickets", "prepare_ticket"}
    specs = [s for s in tool_specs() if s.get("function", {}).get("name") in allowed_tools]
    last_step = (step >= max_steps - 1)
    tool_choice = "none" if last_step else "auto"

    full_messages = messages
    if not any(m.get("role") == "system" for m in messages):
        full_messages = [{"role": "system", "content": _ticket_system_prompt()}] + messages

    tracer = configurable.get("tracer")
    if tracer:
        with tracer.generation(f"TicketWorker轮{step + 1}", model=getattr(model, "model", acfg.LLM_MODEL)) as gen_span:
            turn: ModelTurn = model.complete_with_tools(full_messages, specs, tool_choice)
            gen_span.record(
                output={"toolCalls": [c.name for c in turn.tool_calls], "hasToolCalls": turn.has_tool_calls},
                tokens_in=turn.usage.tokens_in,
                tokens_out=turn.usage.tokens_out,
                tokens_source=turn.usage.tokens_source
            )
    else:
        turn = model.complete_with_tools(full_messages, specs, tool_choice)

    if not turn.has_tool_calls:
        evidence = turn.content or "已完成工单流转与草稿整理"
        return {
            "step": step + 1,
            "latest_tool_calls": [],
            "ticket_evidence": evidence,
            "audit_trail": [f"【TicketWorker】完成工单事务决策"]
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
        "audit_trail": [f"【TicketWorker】第 {step + 1} 轮决策调工具: {[c.name for c in turn.tool_calls]}"]
    }


def ticket_tool_node(state: TicketSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """工单专家工具执行节点。"""
    configurable = (config or {}).get("configurable", {})
    ctx: ToolContext = configurable.get("ctx")
    tool_calls = state.get("latest_tool_calls", [])

    tool_messages: List[Dict[str, Any]] = []
    audit_logs: List[str] = []

    for call in tool_calls:
        call_id = call.get("id")
        name = call.get("name")
        args = call.get("arguments", {})

        result = dispatch(name, args, ctx)
        tool_messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": json.dumps(result, ensure_ascii=False)
        })
        audit_logs.append(f"【TicketWorker】执行工具 {name} 完成 (成功={result.get('success', False)})")

    # 同步可能由 prepare_ticket 产出的草稿
    draft_dict = ctx.draft.model_dump() if ctx and ctx.draft else None

    return {
        "messages": tool_messages,
        "latest_tool_calls": [],
        "ticket_draft": draft_dict,
        "audit_trail": audit_logs
    }


def should_continue(state: TicketSubagentState) -> str:
    calls = state.get("latest_tool_calls") or []
    if calls:
        if state.get("step", 0) >= state.get("max_steps", 3):
            return END
        return "ticket_tool_node"
    return END


def build_ticket_subagent(checkpointer: Optional[BaseCheckpointSaver] = None):
    """编译独立的 TicketWorker LangGraph 子状态图。"""
    workflow = StateGraph(TicketSubagentState)
    workflow.add_node("ticket_model_node", ticket_model_node)
    workflow.add_node("ticket_tool_node", ticket_tool_node)

    workflow.add_edge(START, "ticket_model_node")
    workflow.add_conditional_edges("ticket_model_node", should_continue, {
        "ticket_tool_node": "ticket_tool_node",
        END: END
    })
    workflow.add_edge("ticket_tool_node", "ticket_model_node")

    return workflow.compile(checkpointer=checkpointer)
