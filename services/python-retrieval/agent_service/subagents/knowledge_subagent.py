# -*- coding: utf-8 -*-
"""垂直领域子智能体：KnowledgeSubagent (知识排障专家)。

基于 LangGraph 编排的自适应图谱与双路检索子状态图：
1. knowledge_router_node:
   深入分析员工故障提问意图（SINGLE_DIMENSION 单维事实 vs MULTI_HOP_RELATIONAL 多维复杂因果）。
2. 条件边分流 (route_by_difficulty):
   - 困难多维问题 ➔ complex_graphrag_node (激活 Neo4j BFS 多跳拓扑推导 + Dense/BM25 双路召回 + Rerank)
   - 简单单维问题 ➔ simple_hybrid_retrieval_node (直接执行 Dense + BM25 双路召回，跳过 Neo4j 极速响应)
3. synthesize_evidence_node:
   汇聚检索与图谱因果事实，调用模型提炼结构化排障方案与依据版本（used_version_ids）。
"""

import json
import logging
import operator
import re
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from .. import config as acfg
from ..model_client import ModelClient, ModelTurn
from ..tools import ToolContext, dispatch, tool_specs

log = logging.getLogger(__name__)


class KnowledgeSubagentState(TypedDict):
    """知识排障子图局部状态契约。"""
    question: str
    messages: Annotated[List[Dict[str, Any]], operator.add]
    step: int
    max_steps: int
    intent: Optional[str]                  # "SINGLE_DIMENSION" 或 "MULTI_HOP_RELATIONAL"
    needs_graph: bool                      # 简单走 False，困难多维走 True
    extracted_entities: List[str]          # 提取的关键实体
    retrieval_items: List[Dict[str, Any]]  # 召回结果条目
    latest_tool_calls: List[Dict[str, Any]]
    knowledge_evidence: Optional[str]      # 最终沉淀排障证据
    used_version_ids: List[str]            # 实际依据的版本 ID
    audit_trail: Annotated[List[str], operator.add]


def _knowledge_system_prompt() -> str:
    return """你是一位精通企业 IT 办公技术排障的资深工程师（知识专家）。
你的职责是：
1. 深入分析员工的故障症状，结合检索到的企业知识库参考资料进行整合与归纳；
2. 严禁原样照抄或直接倾倒知识卡片，必须以清晰、专业、结构化的 Markdown 格式输出逐步排查与处置指南；
3. 输出包含：故障可能原因分析、针对性的排查步骤（有序编号列表）、注意事项与后续操作；
4. 保持语气专业诚恳，格式采用标准 Markdown（小标题、序号列表、重点加粗）；
5. 严格禁止索要用户密码或提供高风险系统破坏命令。"""


_adaptive_router: Optional[Any] = None

def _get_adaptive_router():
    global _adaptive_router
    if _adaptive_router is None:
        try:
            from rag_pipeline.graph.router import AdaptiveQueryRouter
            _adaptive_router = AdaptiveQueryRouter()
        except Exception as e:
            log.warning("初始化 AdaptiveQueryRouter 失败: %s", e)
    return _adaptive_router


def knowledge_router_node(state: KnowledgeSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """步骤 1：分析员工提问特征，判定意图（单维事实 vs 困难多维关联）。"""
    question = state.get("question", "")

    needs_graph = False
    intent = "SINGLE_DIMENSION"
    entities: List[str] = []
    decision_reason = ""

    # 1. 优先调用 AdaptiveQueryRouter (具备 LLM One-Pass 与全套领域拓扑/CMDB规则)
    router = _get_adaptive_router()
    if router:
        try:
            res = router.analyze(question)
            needs_graph = bool(res.needs_graph)
            intent = "MULTI_HOP_RELATIONAL" if needs_graph else "SINGLE_DIMENSION"
            entities = list(res.extracted_entities or [])
            decision_reason = res.reason or ""
        except Exception as e:
            log.warning("AdaptiveQueryRouter 判别异常: %s", e)

    # 2. 深度复合与 CMDB 资产关联特征增强兜底
    if not needs_graph:
        complex_patterns = [
            r"691", r"同时", r"并且", r"而且", r"联动", r"因果", r"关系",
            r"关联", r"导致", r"根因", r"拓扑", r"图谱",
            r"跨系统", r"手机邮箱.*vpn|vpn.*手机邮箱", r"ad账号.*vpn|vpn.*ad账号",
            r"(财务|报销|erp|crm|502|bad gateway).*(运维|团队|组|网络|通道|vpn|前置|提单)",
            r"(运维|团队|组|网络|通道|vpn|前置|提单).*(财务|报销|erp|crm|502|bad gateway)",
            r"(连续.*输错|输错.*次|几次.*锁|现行.*规章|最新.*规章|新规|旧规|自动解锁|自动恢复)",
            r"(修改.*密码|新密码|换了密码).*(outlook|邮箱|弹窗|不断提示|又连不上|vpn)",
            r"(appcrash|闪退|崩溃|事件.*1000).*(vc\+\+|运行库|\.net)",
            r"(dns_probe_finished_nxdomain|nxdomain|dns.*污染|dns.*缓存).*(flushdns|ipconfig|223\.5\.5\.5|阿里dns|网页.*打不开)",
            r"(蓝屏|bsod|minidump|dump|bluescreen).*(驱动|内存|sfc|bluescreenview)"
        ]
        if any(re.search(pat, question, re.IGNORECASE) for pat in complex_patterns):
            needs_graph = True
            intent = "MULTI_HOP_RELATIONAL"
            decision_reason = "命中复合多维/CMDB资产流转拓扑规则"

    if needs_graph and not entities:
        q_lower = question.lower()
        if "vpn" in q_lower or "ssl" in q_lower:
            entities.append("SSL VPN")
        if "691" in question:
            entities.append("VPN 691")
        if "邮箱" in question or "邮件" in question:
            entities.append("移动端邮件客户端旧密码轮询")
        if "ad" in q_lower or "账号" in question or "锁定" in question:
            entities.append("AD域账号锁定")
        if "erp" in q_lower or "报销" in question or "502" in question or "财务" in question:
            entities.extend(["财务报销系统", "IT系统组"])
        if "蓝屏" in question or "bsod" in q_lower:
            entities.append("蓝屏死机")
        if "dns" in q_lower:
            entities.append("DNS解析")

    log_msg = f"【KnowledgeWorker 子图】意图识别完成：判定为 [{'困难多维问题（走 Neo4j 拓扑推导 + 双路召回）' if needs_graph else '简单单维问题（走直接双路召回）'}] (needs_graph={needs_graph}, 实体={entities}, 理由={decision_reason})"
    return {
        "intent": intent,
        "needs_graph": needs_graph,
        "extracted_entities": entities,
        "audit_trail": [log_msg]
    }


def route_by_difficulty(state: KnowledgeSubagentState) -> str:
    """条件边：根据困难程度分流。"""
    if state.get("needs_graph", False):
        return "complex_graphrag_node"
    return "simple_hybrid_retrieval_node"


def complex_graphrag_node(state: KnowledgeSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """步骤 2a（困难多维通道）：调度工具执行 Neo4j 拓扑 BFS 因果推导 + 双路召回。"""
    configurable = (config or {}).get("configurable", {})
    ctx: ToolContext = configurable.get("ctx")
    model = configurable.get("model_client")
    cb = getattr(model, "stream_callback", None)
    if cb:
        try:
            cb("stage", {"stage": "RETRIEVING", "message": "KnowledgeWorker：检测到复杂多维关联，正在激活 Neo4j 拓扑因果演绎与双路召回..."})
        except Exception:
            pass

    question = state.get("question", "")

    tool_args = {"query": question, "needs_graph": True}
    res = dispatch("search_knowledge", tool_args, ctx)

    items = res.get("items") or []
    initial_versions = list(state.get("used_version_ids") or [])
    if initial_versions:
        used_versions = initial_versions
    else:
        used_versions = [i.get("versionId") for i in items if i.get("versionId")]

    tool_msg = {
        "role": "tool",
        "tool_call_id": "call_complex_graphrag",
        "name": "search_knowledge",
        "content": json.dumps(res, ensure_ascii=False)
    }

    return {
        "messages": [tool_msg],
        "retrieval_items": items,
        "used_version_ids": used_versions,
        "audit_trail": [f"【KnowledgeWorker 子图】走困难多维通道：激活 Neo4j 因果推导拓扑检索 + 双路召回（获取 {len(items)} 条证据，含图谱因果链={res.get('graph_enhanced', False)}）"]
    }


def simple_hybrid_retrieval_node(state: KnowledgeSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """步骤 2b（简单单维通道）：直接执行 Dense + BM25 双路召回，跳过 Neo4j 图查询。"""
    configurable = (config or {}).get("configurable", {})
    ctx: ToolContext = configurable.get("ctx")
    model = configurable.get("model_client")
    cb = getattr(model, "stream_callback", None)
    if cb:
        try:
            cb("stage", {"stage": "RETRIEVING", "message": "KnowledgeWorker：正在执行向量 + BM25 双路知识召回与重排..."})
        except Exception:
            pass

    question = state.get("question", "")

    tool_args = {"query": question, "needs_graph": False}
    res = dispatch("search_knowledge", tool_args, ctx)

    items = res.get("items") or []
    initial_versions = list(state.get("used_version_ids") or [])
    if initial_versions:
        used_versions = initial_versions
    else:
        used_versions = [i.get("versionId") for i in items if i.get("versionId")]

    tool_msg = {
        "role": "tool",
        "tool_call_id": "call_simple_hybrid",
        "name": "search_knowledge",
        "content": json.dumps(res, ensure_ascii=False)
    }

    return {
        "messages": [tool_msg],
        "retrieval_items": items,
        "used_version_ids": used_versions,
        "audit_trail": [f"【KnowledgeWorker 子图】走简单单维通道：直接执行 Dense + BM25 双路召回，跳过 Neo4j（获取 {len(items)} 条证据）"]
    }


def synthesize_evidence_node(state: KnowledgeSubagentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """步骤 3：综合检索事实与因果链，调用模型提炼结构化 Markdown 排障依据并完成双路 Top3 整合。"""
    configurable = (config or {}).get("configurable", {})
    model: Optional[ModelClient] = configurable.get("model_client")
    items = state.get("retrieval_items") or []
    question = state.get("question", "")

    # 双路召回选出 top3
    top_items = items[:3]

    cb = getattr(model, "stream_callback", None)
    if cb:
        try:
            cb("stage", {
                "stage": "SYNTHESIZING",
                "message": f"KnowledgeWorker：已召回 Top {len(top_items)} 篇核心排障依据，正在整合提炼方案..."
            })
        except Exception:
            pass

    reference_parts = []
    for idx, item in enumerate(top_items, 1):
        title = item.get("title") or "未命名知识条目"
        summary = item.get("summary") or item.get("snippet") or item.get("content") or ""
        reference_parts.append(f"【参考资料 {idx}】《{title}》\n{summary}")
    references_text = "\n\n".join(reference_parts) if reference_parts else "暂未检索到直接匹配的知识库文章。"

    # 版本复核一致性：优先采用 Top3 实际依据的 versionId，且严格维护初始 material 子集
    candidate_versions = [i.get("versionId") for i in top_items if i.get("versionId")]
    initial_versions = list(state.get("used_version_ids") or [])
    if initial_versions:
        matched = [v for v in candidate_versions if v in initial_versions]
        used_versions = matched if matched else initial_versions
    else:
        used_versions = candidate_versions

    user_prompt = (
        f"员工咨询问题：\n{question}\n\n"
        f"企业 IT 知识库召回的前 3 篇参考资料如下：\n"
        f"--------------------\n"
        f"{references_text}\n"
        f"--------------------\n\n"
        f"请基于上述参考资料，结合 IT 运维专业知识，对员工的问题进行整合分析，提供条理清晰、排版优雅的排障指引（采用 Markdown 格式，包含故障可能原因、分步骤排查操作指南、注意事项等，严禁原样照抄知识卡片）。"
    )

    full_messages = [
        {"role": "system", "content": _knowledge_system_prompt()},
        {"role": "user", "content": user_prompt}
    ]

    evidence_text = ""
    if model and hasattr(model, "complete_with_tools"):
        tracer = configurable.get("tracer")
        try:
            if tracer:
                with tracer.generation("KnowledgeWorker排障生成", model=getattr(model, "model", acfg.LLM_MODEL)) as gen_span:
                    turn: ModelTurn = model.complete_with_tools(full_messages, tools=[], tool_choice="none")
                    evidence_text = turn.content or ""
                    gen_span.record(
                        output=evidence_text,
                        tokens_in=turn.usage.tokens_in,
                        tokens_out=turn.usage.tokens_out,
                        tokens_source=turn.usage.tokens_source
                    )
            else:
                turn: ModelTurn = model.complete_with_tools(full_messages, tools=[], tool_choice="none")
                evidence_text = turn.content or ""
        except Exception as e:
            log.warning("模型总结排障证据异常: %s", e)

    if not evidence_text:
        parts = []
        for idx, item in enumerate(top_items, 1):
            title = item.get("title", "")
            summary = item.get("summary", "")
            parts.append(f"### {idx}. {title}\n{summary}")
        evidence_text = "\n\n".join(parts) if parts else "已完成知识库排障检索，暂未检索到直接匹配的排障方案。"

    return {
        "knowledge_evidence": evidence_text,
        "used_version_ids": used_versions,
        "retrieval_items": top_items,
        "audit_trail": ["【KnowledgeWorker 子图】完成双路召回 Top-3 证据汇总与专业 Markdown 排障方案提炼"]
    }


def build_knowledge_subagent(checkpointer: Optional[BaseCheckpointSaver] = None):
    """编译 KnowledgeWorker LangGraph 子状态图。

    拓扑架构：
    START ➔ knowledge_router_node ➔ (route_by_difficulty)
           ├── [needs_graph=True]  ➔ complex_graphrag_node ──────┐
           └── [needs_graph=False] ➔ simple_hybrid_retrieval_node ┤
                                                                 ▼
                                                     synthesize_evidence_node ➔ END
    """
    workflow = StateGraph(KnowledgeSubagentState)

    workflow.add_node("knowledge_router_node", knowledge_router_node)
    workflow.add_node("complex_graphrag_node", complex_graphrag_node)
    workflow.add_node("simple_hybrid_retrieval_node", simple_hybrid_retrieval_node)
    workflow.add_node("synthesize_evidence_node", synthesize_evidence_node)

    workflow.add_edge(START, "knowledge_router_node")
    workflow.add_conditional_edges(
        "knowledge_router_node",
        route_by_difficulty,
        {
            "complex_graphrag_node": "complex_graphrag_node",
            "simple_hybrid_retrieval_node": "simple_hybrid_retrieval_node"
        }
    )
    workflow.add_edge("complex_graphrag_node", "synthesize_evidence_node")
    workflow.add_edge("simple_hybrid_retrieval_node", "synthesize_evidence_node")
    workflow.add_edge("synthesize_evidence_node", END)

    return workflow.compile(checkpointer=checkpointer)
