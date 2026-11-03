# -*- coding: utf-8 -*-
"""基于 LangGraph 的 ReAct 智能体编排状态图 (Agent Graph)。

将原先手写 Python for 循环模拟的 ReAct 决策过程全面重构为显式有向图 (StateGraph)：
  START ──> model_node ──(should_continue)──┬──[有工具调用]──> tool_node ──┐
                 ▲                          │                             │
                 │                          └──[无工具调用]──> END         │
                 └────────────────────────────────────────────────────────┘

优势：
1. 节点与边职责单一透明，原生支持有向图生命周期管理；
2. 搭载 Checkpointer 检查点持久化，保留多轮思考快照；
3. 原生支持向量检索工具 `search_knowledge`、工单查询与草稿生成的闭环流转；
4. 完美保持上游 APM 链路追踪与企业级白名单安全约束。
"""

import json
import logging
import operator
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from . import config as acfg
from .model_client import ModelClient, ModelTurn
from .tools import ToolContext, dispatch

log = logging.getLogger(__name__)


# ==============================================================================
# 1. LangGraph State 结构契约 (TypedDict)
# ==============================================================================

class AgentGraphState(TypedDict):
    """LangGraph 智能体状态：纯原生可序列化数据结构。"""
    # 消息列表累加器：保留完整对话上下文与工具执行日志
    messages: Annotated[List[Dict[str, Any]], operator.add]
    user_id: str
    role: str
    request_id: str
    question: str
    step: int
    max_steps: int
    # 当前轮次待执行的工具调用列表
    latest_tool_calls: List[Dict[str, Any]]
    # 模型输出的最终文本答复（达到终态时填充）
    final_content: Optional[str]
    # 建单草稿缓存数据（由 prepare_ticket 产出）
    draft: Optional[Dict[str, Any]]
    # 状态图全生命周期审计轨迹累加
    audit_trail: Annotated[List[str], operator.add]


# ==============================================================================
# 2. 状态图计算节点实现 (Nodes)
# ==============================================================================

def model_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """模型决策节点：驱动 LLM 思考，产出工具调用指令或最终回答。"""
    configurable = (config or {}).get("configurable", {})
    model: ModelClient = configurable.get("model_client")
    specs: List[Dict[str, Any]] = configurable.get("specs", [])
    tracer = configurable.get("tracer")

    step = state.get("step", 0)
    max_steps = state.get("max_steps", acfg.MAX_STEPS)
    messages = state.get("messages", [])

    # 步数安全熔断：最后一轮强制 tool_choice="none"，逼出最终答案，防工具死循环 (RD-007)
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
        # 模型已输出最终结论
        return {
            "step": step + 1,
            "latest_tool_calls": [],
            "final_content": turn.content or "",
            "audit_trail": [f"【ReAct 第 {step + 1} 轮】模型完成推理，直接产出最终结构化答复"]
        }

    # 包装模型的 Assistant 工具调用消息
    tool_calls_dict = [
        {"id": c.id, "name": c.name, "arguments": c.arguments}
        for c in turn.tool_calls
    ]
    assistant_msg = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.name,
                    "arguments": json.dumps(c.arguments, ensure_ascii=False)
                }
            }
            for c in turn.tool_calls
        ]
    }
    tool_names = [c.name for c in turn.tool_calls]
    return {
        "step": step + 1,
        "latest_tool_calls": tool_calls_dict,
        "messages": [assistant_msg],
        "audit_trail": [f"【ReAct 第 {step + 1} 轮】模型决定发起工具调用: {tool_names}"]
    }


def tool_node(state: AgentGraphState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """工具派发执行节点：执行 search_knowledge、query_my_tickets 或 prepare_ticket 并回传结果。"""
    configurable = (config or {}).get("configurable", {})
    ctx: ToolContext = configurable.get("ctx")
    tracer = configurable.get("tracer")

    tool_calls = state.get("latest_tool_calls", [])
    tool_messages = []
    executed_names = []

    for call in tool_calls:
        name = call["name"]
        args = call["arguments"]
        call_id = call["id"]
        executed_names.append(name)

        if tracer:
            with tracer.span(f"tool.{name}") as span:
                span.record(input=args)
                result = dispatch(name, args, ctx)
                span.record(output={"success": result.get("success")})
        else:
            result = dispatch(name, args, ctx)

        tool_messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(result, ensure_ascii=False)
        })

    draft_dict = ctx.draft.model_dump() if (ctx and ctx.draft) else None
    return {
        "messages": tool_messages,
        "latest_tool_calls": [],
        "draft": draft_dict,
        "audit_trail": [f"【工具执行】完成工具执行: {executed_names}，结果已以 role=tool 形式回写消息流"]
    }


# ==============================================================================
# 3. 条件边逻辑 (Conditional Edges)
# ==============================================================================

def should_continue(state: AgentGraphState) -> str:
    """条件路由：根据最新状态决定是流向工具执行，还是终止流转。"""
    # 1. 已获取最终答复文本 -> 终结
    if state.get("final_content") is not None:
        return END

    # 2. 存在待执行工具调用
    if state.get("latest_tool_calls"):
        # 超限熔断防护
        if state.get("step", 0) >= state.get("max_steps", acfg.MAX_STEPS):
            log.warning("[LangGraph] ReAct 步数已达到最大限制 %s，强制结束", state.get("max_steps"))
            return END
        return "tool_node"

    return END


# ==============================================================================
# 4. 图编译工厂函数 (Graph Builder)
# ==============================================================================

def build_react_agent_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """编译并构建可运行的 LangGraph ReAct 状态图实例。"""
    workflow = StateGraph(AgentGraphState)

    # 注册节点
    workflow.add_node("model_node", model_node)
    workflow.add_node("tool_node", tool_node)

    # 设定流转拓扑
    workflow.add_edge(START, "model_node")
    workflow.add_conditional_edges(
        "model_node",
        should_continue,
        {
            "tool_node": "tool_node",
            END: END
        }
    )
    workflow.add_edge("tool_node", "model_node")

    return workflow.compile(checkpointer=checkpointer)
