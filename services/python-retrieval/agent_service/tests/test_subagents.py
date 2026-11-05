# -*- coding: utf-8 -*-
"""垂直领域子智能体（KnowledgeWorker 与 TicketWorker）单元测试。

验证：
1. KnowledgeWorker 子图架构：意图判定分流（困难多维 Neo4j+双路召回 vs 简单纯双路召回）与事实证据总结
2. TicketWorker 子图架构：ReAct 循环调用 query_my_tickets 与 prepare_ticket 产出草稿
"""

import json
from typing import Any, Dict, List
import pytest

from agent_service.model_client import ModelClient, ModelTurn, ToolCall, ModelUsage
from agent_service.tools import ToolContext
from agent_service.subagents.knowledge_subagent import (
    build_knowledge_subagent,
    KnowledgeSubagentState,
)
from agent_service.subagents.ticket_subagent import (
    build_ticket_subagent,
    TicketSubagentState,
)


class MockModelClient(ModelClient):
    """测试用 Mock 客户端。"""

    def __init__(self, turns: List[ModelTurn]):
        self.turns = list(turns)
        self.call_count = 0

    def complete_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                            tool_choice: str = "auto") -> ModelTurn:
        if self.call_count >= len(self.turns):
            return ModelTurn([], "{}", None, ModelUsage(10, 10, 20, True))
        turn = self.turns[self.call_count]
        self.call_count += 1
        return turn


def test_knowledge_subagent_run(monkeypatch):
    """测试 KnowledgeSubagent 能检索知识并由模型输出排障证据。"""
    from agent_service import tools
    monkeypatch.setattr(
        tools,
        "_search_knowledge",
        lambda args, ctx: {"success": True, "total": 1, "items": [{"versionId": "ver-vpn-809", "title": "VPN 809排障", "summary": "检查UDP端口"}]}
    )

    turn = ModelTurn(
        tool_calls=[],
        content="VPN 809排障指引：请核查本地 UDP 500/4500 端口是否被家庭路由器拦截。",
        raw_message=None,
        usage=ModelUsage(20, 20, 40, True)
    )
    mock_model = MockModelClient([turn])
    ctx = ToolContext("U1001", "EMPLOYEE", "req-test-k", question="VPN 809怎么办")

    graph = build_knowledge_subagent()
    init_state: KnowledgeSubagentState = {
        "question": "VPN 809怎么办",
        "messages": [{"role": "user", "content": "VPN 809怎么办"}],
        "step": 0,
        "max_steps": 3,
        "intent": None,
        "needs_graph": False,
        "extracted_entities": [],
        "retrieval_items": [],
        "latest_tool_calls": [],
        "knowledge_evidence": None,
        "used_version_ids": ["ver-vpn-809"],
        "audit_trail": []
    }
    config = {
        "configurable": {
            "model_client": mock_model,
            "ctx": ctx,
        }
    }

    final_state = graph.invoke(init_state, config=config)
    assert final_state["knowledge_evidence"] is not None
    assert "UDP 500/4500" in final_state["knowledge_evidence"]
    assert mock_model.call_count == 1
    assert any("【KnowledgeWorker 子图】" in log for log in final_state["audit_trail"])


def test_knowledge_subagent_simple_flow(monkeypatch):
    """测试 KnowledgeSubagent 简单单维问题走直接双路召回节点（跳过 Neo4j）。"""
    from agent_service import tools
    called_args = []
    def mock_search(args, ctx):
        called_args.append(args)
        return {"success": True, "total": 1, "items": [{"versionId": "ver-wifi-01", "title": "公司WiFi配置", "summary": "连接 Corp-WiFi"}]}

    monkeypatch.setattr(tools, "_search_knowledge", mock_search)

    ctx = ToolContext("U1001", "EMPLOYEE", "req-test-simple", question="公司WiFi密码是多少")
    graph = build_knowledge_subagent()
    init_state: KnowledgeSubagentState = {
        "question": "公司WiFi密码是多少",
        "messages": [{"role": "user", "content": "公司WiFi密码是多少"}],
        "step": 0,
        "max_steps": 3,
        "intent": None,
        "needs_graph": False,
        "extracted_entities": [],
        "retrieval_items": [],
        "latest_tool_calls": [],
        "knowledge_evidence": None,
        "used_version_ids": [],
        "audit_trail": []
    }

    final_state = graph.invoke(init_state, config={"configurable": {"ctx": ctx}})
    assert final_state["intent"] == "SINGLE_DIMENSION"
    assert final_state["needs_graph"] is False
    assert any("走简单单维通道" in log for log in final_state["audit_trail"])
    assert len(called_args) == 1
    assert called_args[0].get("needs_graph") is False


def test_knowledge_subagent_complex_graph_flow(monkeypatch):
    """测试 KnowledgeSubagent 困难多维问题走 Neo4j 因果推导 + 双路召回节点。"""
    from agent_service import tools
    called_args = []
    def mock_search(args, ctx):
        called_args.append(args)
        return {
            "success": True,
            "total": 1,
            "items": [{
                "versionId": "ver-vpn-691",
                "title": "VPN 691拨号错误",
                "summary": "【知识图谱因果推导】VPN拨号691与移动端邮件客户端密码轮询导致AD账号锁定具备强因果关联。\n排查建议：先解锁AD账号。",
                "snippet": "【知识图谱因果推导】VPN拨号691与移动端邮件客户端密码轮询导致AD账号锁定具备强因果关联。"
            }],
            "graph_enhanced": True
        }

    monkeypatch.setattr(tools, "_search_knowledge", mock_search)

    ctx = ToolContext("U1001", "EMPLOYEE", "req-test-complex", question="在家拨号公司VPN提示691错误，并且手机邮箱一直报错")
    graph = build_knowledge_subagent()
    init_state: KnowledgeSubagentState = {
        "question": "在家拨号公司VPN提示691错误，并且手机邮箱一直报错",
        "messages": [{"role": "user", "content": "在家拨号公司VPN提示691错误，并且手机邮箱一直报错"}],
        "step": 0,
        "max_steps": 3,
        "intent": None,
        "needs_graph": False,
        "extracted_entities": [],
        "retrieval_items": [],
        "latest_tool_calls": [],
        "knowledge_evidence": None,
        "used_version_ids": [],
        "audit_trail": []
    }

    final_state = graph.invoke(init_state, config={"configurable": {"ctx": ctx}})
    assert final_state["intent"] == "MULTI_HOP_RELATIONAL"
    assert final_state["needs_graph"] is True
    assert any("VPN" in e for e in final_state["extracted_entities"])
    assert any("691" in e for e in final_state["extracted_entities"])
    assert any("走困难多维通道" in log for log in final_state["audit_trail"])
    assert len(called_args) == 1
    assert called_args[0].get("needs_graph") is True
    assert "【知识图谱因果推导】" in final_state["knowledge_evidence"]


def test_ticket_subagent_run(monkeypatch):
    """测试 TicketSubagent 能调用 query_my_tickets 与 prepare_ticket 产出草稿。"""
    from agent_service import tools
    monkeypatch.setattr(
        tools,
        "_query_my_tickets",
        lambda args, ctx: {"success": True, "total": 1, "items": [{"id": "TK1001", "title": "笔记本蓝屏", "status": "PROCESSING"}]}
    )

    turn_1 = ModelTurn(
        tool_calls=[ToolCall("call_t1", "query_my_tickets", {"limit": 2})],
        content="",
        raw_message=None,
        usage=ModelUsage(10, 10, 20, True)
    )
    turn_2 = ModelTurn(
        tool_calls=[],
        content="您昨日提报的工单 TK1001（笔记本蓝屏）目前处于 PROCESSING 状态，运维正在加紧处理。",
        raw_message=None,
        usage=ModelUsage(20, 20, 40, True)
    )
    mock_model = MockModelClient([turn_1, turn_2])
    ctx = ToolContext("U1001", "EMPLOYEE", "req-test-t", question="查工单")

    graph = build_ticket_subagent()
    init_state: TicketSubagentState = {
        "question": "查我昨天提的工单进度",
        "messages": [{"role": "user", "content": "查我昨天提的工单进度"}],
        "step": 0,
        "max_steps": 3,
        "latest_tool_calls": [],
        "ticket_evidence": None,
        "ticket_draft": None,
        "audit_trail": []
    }
    config = {
        "configurable": {
            "model_client": mock_model,
            "ctx": ctx,
        }
    }

    final_state = graph.invoke(init_state, config=config)
    assert final_state["ticket_evidence"] is not None
    assert "TK1001" in final_state["ticket_evidence"]
    assert mock_model.call_count == 2
