# -*- coding: utf-8 -*-
"""LangGraph ReAct 智能体编排单元测试。"""

import json
from typing import Any, Dict, List, Optional
import pytest

from agent_service.agent import AgentRunner
from agent_service.contract import AgentChatRequest, AgentTurn, AgentMaterial
from agent_service.graph import build_react_agent_graph
from agent_service.model_client import ModelClient, ModelTurn, ToolCall, ModelUsage, ModelError


class MockModelClient(ModelClient):
    """用于测试的 Mock 模型客户端。"""

    def __init__(self, turns: List[ModelTurn]):
        self.turns = list(turns)
        self.call_count = 0
        self.received_messages = []
        self.received_tool_choices = []

    def complete_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                            tool_choice: str = "auto") -> ModelTurn:
        self.received_messages.append(messages)
        self.received_tool_choices.append(tool_choice)
        if self.call_count >= len(self.turns):
            # 兜底返回空文本
            return ModelTurn([], "{}", None, ModelUsage(10, 10, 20, True))
        turn = self.turns[self.call_count]
        self.call_count += 1
        return turn


def test_react_graph_direct_answer():
    """测试模型直接输出答案，无工具调用，1轮结束。"""
    answer_payload = {
        "replyType": "ANSWER",
        "answerText": "请检查网线连接。",
        "usedVersionIds": ["ver-001"],
        "confidence": 0.95,
        "knowledgeConflict": False,
        "offTopic": False
    }
    mock_turn = ModelTurn(
        tool_calls=[],
        content=json.dumps(answer_payload, ensure_ascii=False),
        raw_message=None,
        usage=ModelUsage(tokens_in=50, tokens_out=30, total_tokens=80, reported=True)
    )
    mock_model = MockModelClient([mock_turn])
    runner = AgentRunner(model_client=mock_model, max_steps=3)

    req = AgentChatRequest(
        question="电脑连不上网怎么办？",
        history=[],
        material=[AgentMaterial(version_id="ver-001", title="网络排障", content="检查网线。")]
    )

    resp = runner.run(req, user_id="U1001", role="EMPLOYEE", request_id="req-test-direct")
    assert resp.reply_type == "ANSWER"
    assert resp.answer_text == "请检查网线连接。"
    assert resp.used_version_ids == ["ver-001"]
    assert resp.confidence == 0.95
    assert mock_model.call_count == 1
    assert mock_model.received_tool_choices[0] == "auto"


def test_react_graph_with_tool_calling(monkeypatch):
    """测试模型在第1轮触发向量检索/工具调用，第2轮反思并输出最终结论。"""
    from agent_service import tools
    # Mock 工具 search_knowledge
    monkeypatch.setattr(
        tools,
        "_search_knowledge",
        lambda args, ctx: {"success": True, "total": 1, "items": [{"articleId": "art-1", "title": "VPN配置", "summary": "配置说明"}]}
    )

    # 第1轮：返回工具调用
    turn_1 = ModelTurn(
        tool_calls=[ToolCall("call_1", "search_knowledge", {"query": "VPN 无法连接"})],
        content=None,
        raw_message=None,
        usage=ModelUsage(tokens_in=60, tokens_out=25, total_tokens=85, reported=True)
    )
    # 第2轮：根据工具返回结果，输出最终答复
    answer_payload = {
        "replyType": "ANSWER",
        "answerText": "请按照 VPN 配置说明重置网络适配器。",
        "usedVersionIds": [],
        "confidence": 0.88,
        "knowledgeConflict": False,
        "offTopic": False
    }
    turn_2 = ModelTurn(
        tool_calls=[],
        content=json.dumps(answer_payload, ensure_ascii=False),
        raw_message=None,
        usage=ModelUsage(tokens_in=120, tokens_out=40, total_tokens=160, reported=True)
    )

    mock_model = MockModelClient([turn_1, turn_2])
    runner = AgentRunner(model_client=mock_model, max_steps=5)

    req = AgentChatRequest(
        question="VPN连不上了，帮我查一下知识库",
        history=[],
        material=[]
    )

    resp = runner.run(req, user_id="U2002", role="EMPLOYEE", request_id="req-test-tools")
    assert resp.reply_type == "ANSWER"
    assert resp.answer_text == "请按照 VPN 配置说明重置网络适配器。"
    assert mock_model.call_count == 2

    # 验证 Checkpointer 历史快照
    history = list(runner.checkpointer.list({"configurable": {"thread_id": "req-test-tools"}}))
    assert len(history) >= 2


def test_react_graph_step_limit_exceeded():
    """测试模型一直发起工具调用，超过 max_steps 时正确熔断并抛出 ModelError。"""
    infinite_tool_turn = ModelTurn(
        tool_calls=[ToolCall("call_inf", "search_knowledge", {"query": "循环"})],
        content=None,
        raw_message=None
    )
    # 模拟两轮都返回工具调用，设置 max_steps=2
    mock_model = MockModelClient([infinite_tool_turn, infinite_tool_turn, infinite_tool_turn])
    runner = AgentRunner(model_client=mock_model, max_steps=2)

    req = AgentChatRequest(
        question="测试死循环",
        history=[],
        material=[]
    )

    with pytest.raises(ModelError, match="ReAct 步数超限"):
        runner.run(req, user_id="U3003", role="EMPLOYEE", request_id="req-test-limit")

    # 验证最后一轮传递了 tool_choice="none"
    assert mock_model.received_tool_choices[-1] == "none"


def test_fastapi_app_integration():
    """测试 FastAPI app 经由 LangGraph runner 成功端到端返回。"""
    from starlette.testclient import TestClient
    from agent_service.app import create_app

    answer_payload = {
        "replyType": "ANSWER",
        "answerText": "网卡已恢复正常。",
        "usedVersionIds": [],
        "confidence": 0.9,
        "knowledgeConflict": False,
        "offTopic": False
    }
    mock_turn = ModelTurn(
        tool_calls=[],
        content=json.dumps(answer_payload, ensure_ascii=False),
        raw_message=None,
        usage=ModelUsage(10, 10, 20, True)
    )
    mock_model = MockModelClient([mock_turn])
    runner = AgentRunner(model_client=mock_model, max_steps=3)
    app = create_app(runner=runner)

    client = TestClient(app)
    resp = client.post(
        "/api/v1/agent/chat",
        headers={"X-User-Id": "U888", "X-User-Role": "EMPLOYEE", "X-Request-Id": "req-fastapi-test"},
        json={"question": "网络好了吗？", "history": [], "material": []}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["replyType"] == "ANSWER"
    assert data["data"]["answerText"] == "网卡已恢复正常。"
