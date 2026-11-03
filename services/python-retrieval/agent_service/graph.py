# -*- coding: utf-8 -*-
"""基于 LangGraph 的主从多智能体编排状态图 (Supervisor-Subagent Graph)。

实现 Supervisor-Worker 工业级主从拓扑：
1. 节点与子图：
   - guard_input: 输入安全护栏 (Prompt 越狱注入拦截 + PII 敏感信息脱敏进 Vault)
   - supervisor: 主管总控决策中心 (根据问题特征自适应调度子智能体)
   - knowledge_worker: 知识排障子图 (独立 ReAct 循环，专职 8301 知识检索)
   - ticket_worker: 工单流转子图 (独立 ReAct 循环，专职 8201 查单与规范草稿)
   - formulator: 终审收敛节点 (汇总多源事实证据，组装严格 6 键 JSON 契约)
   - guard_output: 输出安全护栏 (将 Vault 中真实敏感信息无损还原)
2. 拓扑收敛性：
   - 子图执行完毕后 100% 回环至 Supervisor，避免点对点死锁循环。
   - 保留 Checkpointer 审计快照与 Langfuse 观测追踪。
"""

import json
import logging
import operator
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from . import config as acfg
from .model_client import ModelClient, ModelTurn, ModelError
from .tools import ToolContext, dispatch, tool_specs
from .subagents.knowledge_subagent import (
    build_knowledge_subagent,
    KnowledgeSubagentState,
)
from .subagents.ticket_subagent import (
    build_ticket_subagent,
    TicketSubagentState,
)
from .supervisor import (
    SupervisorTeamState,
    input_guard_node,
    supervisor_router_node,
    formulator_node,
    output_guard_node,
)

log = logging.getLogger(__name__)


# ==============================================================================
# 1. 经典单 Agent ReAct 状态契约 (兼容保留)
# ==============================================================================

class AgentGraphState(TypedDict):
    """LangGraph 单智能体状态：纯原生可序列化数据结构。"""
    messages: Annotated[List[Dict[str, Any]], operator.add]
    user_id: str
    role: str
    request_id: str
    question: str
    step: int
    max_steps: int
    latest_tool_calls: List[Dict[str, Any]]
    final_content: Optional[str]
    draft: Optional[Dict[str, Any]]
    audit_trail: Annotated[List[str], operator.add]


def model_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """单智能体模型决策节点。"""
    configurable = (config or {}).get("configurable", {})
    model: ModelClient = configurable.get("model_client")
    specs: List[Dict[str, Any]] = configurable.get("specs", [])
    tracer = configurable.get("tracer")

    step = state.get("step", 0)
    max_steps = state.get("max_steps", acfg.MAX_STEPS)
    messages = state.get("messages", [])

    last_step = (step >= max_steps - 1)
    tool_choice = "none" if last_step else "auto"

    if tracer:
        with tracer.generation(f"ReAct轮{step + 1}", model=acfg.LLM_MODEL) as gen_span:
            turn: ModelTurn = model.complete_with_tools(messages, specs, tool_choice)
            gen_span.record(
                output={"toolCalls": [c.name for c in turn.tool_calls], "hasToolCalls": turn.has_tool_calls},
                tokens_in=turn.usage.tokens_in,
                tokens_out=turn.usage.tokens_out,
                tokens_source=turn.usage.tokens_source
            )
    else:
        turn = model.complete_with_tools(messages, specs, tool_choice)

    if not turn.has_tool_calls:
        return {
            "step": step + 1,
            "latest_tool_calls": [],
            "final_content": turn.content or "",
            "audit_trail": [f"【ReAct 第 {step + 1} 轮】模型完成推理，直接产出最终结构化答复"]
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
        "audit_trail": [f"【ReAct 第 {step + 1} 轮】决策调用工具: {[c.name for c in turn.tool_calls]}"]
    }


def tool_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """单智能体工具执行节点。"""
    configurable = (config or {}).get("configurable", {})
    ctx: ToolContext = configurable.get("ctx")
    tracer = configurable.get("tracer")
    tool_calls = state.get("latest_tool_calls", [])

    tool_messages: List[Dict[str, Any]] = []
    audit_logs: List[str] = []

    for call in tool_calls:
        call_id = call.get("id")
        name = call.get("name")
        args = call.get("arguments", {})

        if tracer:
            with tracer.span(name=f"tool:{name}", kind="TOOL", input={"arguments": args}) as span:
                result = dispatch(name, args, ctx)
                span.record(output=result)
        else:
            result = dispatch(name, args, ctx)

        tool_messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": json.dumps(result, ensure_ascii=False)
        })
        audit_logs.append(f"【工具执行】工具 {name} 完成，结果已注入对话上下文 (成功={result.get('success', False)})")

    draft_dict = ctx.draft.model_dump() if ctx and ctx.draft else None
    return {
        "messages": tool_messages,
        "latest_tool_calls": [],
        "draft": draft_dict,
        "audit_trail": audit_logs
    }


def should_continue(state: AgentGraphState) -> str:
    calls = state.get("latest_tool_calls") or []
    if calls:
        if state.get("step", 0) >= state.get("max_steps", acfg.MAX_STEPS):
            return END
        return "tool_node"
    return END


def build_react_agent_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """编译经典单 Agent ReAct 状态图。"""
    workflow = StateGraph(AgentGraphState)
    workflow.add_node("model_node", model_node)
    workflow.add_node("tool_node", tool_node)

    workflow.add_edge(START, "model_node")
    workflow.add_conditional_edges("model_node", should_continue, {
        "tool_node": "tool_node",
        END: END
    })
    workflow.add_edge("tool_node", "model_node")
    return workflow.compile(checkpointer=checkpointer)


# ==============================================================================
# 2. Supervisor-Worker 主从多智能体编排状态图 (核心实现)
# ==============================================================================

def knowledge_worker_node(state: SupervisorTeamState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """知识排障子智能体适配节点。"""
    configurable = (config or {}).get("configurable", {})
    subgraph = build_knowledge_subagent()
    question = state.get("sanitized_question") or state.get("question", "")
    max_steps = configurable.get("max_steps", 3)

    child_state: KnowledgeSubagentState = {
        "question": question,
        "messages": [{"role": "user", "content": question}],
        "step": 0,
        "max_steps": max_steps,
        "latest_tool_calls": [],
        "knowledge_evidence": None,
        "used_version_ids": state.get("used_version_ids", []),
        "audit_trail": []
    }
    result = subgraph.invoke(child_state, config=config)
    evidence = result.get("knowledge_evidence")
    if evidence is None and result.get("step", 0) >= max_steps:
        raise ModelError("ReAct 步数超限")

    return {
        "knowledge_evidence": evidence or "已排查相关知识",
        "used_version_ids": result.get("used_version_ids", []),
        "audit_trail": result.get("audit_trail", [])
    }


def ticket_worker_node(state: SupervisorTeamState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """工单流转子智能体适配节点。"""
    configurable = (config or {}).get("configurable", {})
    subgraph = build_ticket_subagent()
    question = state.get("sanitized_question") or state.get("question", "")

    child_state: TicketSubagentState = {
        "question": question,
        "messages": [{"role": "user", "content": question}],
        "step": 0,
        "max_steps": configurable.get("max_steps", 3),
        "latest_tool_calls": [],
        "ticket_evidence": None,
        "ticket_draft": state.get("ticket_draft"),
        "audit_trail": []
    }
    result = subgraph.invoke(child_state, config=config)
    evidence = result.get("ticket_evidence")
    if evidence is None and result.get("step", 0) >= configurable.get("max_steps", 3):
        raise ModelError("ReAct 步数超限")

    return {
        "ticket_evidence": evidence or "已完成工单流转核验",
        "ticket_draft": result.get("ticket_draft"),
        "audit_trail": result.get("audit_trail", [])
    }


def build_subagent_supervisor_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """编译工业级 Supervisor-Subagent 主从多智能体编排状态图。"""
    workflow = StateGraph(SupervisorTeamState)

    # 1. 注册核心节点
    workflow.add_node("guard_input", input_guard_node)
    workflow.add_node("supervisor", supervisor_router_node)
    workflow.add_node("knowledge_worker", knowledge_worker_node)
    workflow.add_node("ticket_worker", ticket_worker_node)
    workflow.add_node("formulator", formulator_node)
    workflow.add_node("guard_output", output_guard_node)

    # 2. 拓扑连线
    workflow.add_edge(START, "guard_input")
    workflow.add_edge("guard_input", "supervisor")

    # Supervisor 条件路由分发
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state["next_action"],
        {
            "CALL_KNOWLEDGE": "knowledge_worker",
            "CALL_TICKET": "ticket_worker",
            "FINISH": "formulator"
        }
    )

    # 子图执行后统一收敛返回 Supervisor 重新决策
    workflow.add_edge("knowledge_worker", "supervisor")
    workflow.add_edge("ticket_worker", "supervisor")

    # 终审出网流
    workflow.add_edge("formulator", "guard_output")
    workflow.add_edge("guard_output", END)

    return workflow.compile(checkpointer=checkpointer)
