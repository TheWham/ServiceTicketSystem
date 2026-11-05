# -*- coding: utf-8 -*-
import json
from typing import Any, Dict, List

from fastapi.testclient import TestClient

from agent_service.agent import AgentRunner
from agent_service.app import create_app
from agent_service.contract import AgentChatRequest
from agent_service.cost_governance import CostGovernor, ModelRouter, TokenBudgetManager
from agent_service.model_client import ModelClient, ModelTurn, ModelUsage


class MockStreamModelClient(ModelClient):
    """测试流式专用的 Mock 模型客户端。"""

    def __init__(self, turns: List[ModelTurn]):
        self.turns = list(turns)
        self.call_count = 0
        self.stream_callback = None

    def clone_with_model(self, model_name: str, stream_callback: Any = None) -> "MockStreamModelClient":
        cloned = MockStreamModelClient(self.turns)
        cloned.call_count = self.call_count
        cloned.stream_callback = stream_callback if stream_callback is not None else self.stream_callback
        return cloned

    def complete_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                            tool_choice: str = "auto", model_override: str = None) -> ModelTurn:
        if self.call_count >= len(self.turns):
            turn = ModelTurn([], "{}", None, ModelUsage(10, 10, 20, True))
        else:
            turn = self.turns[self.call_count]
            self.call_count += 1

        if self.stream_callback is not None and turn.content:
            # 模拟逐 chunk 回调
            from agent_service.model_client import StreamingAnswerExtractor
            extractor = StreamingAnswerExtractor()
            # 拆为 3 段推送
            step_len = max(1, len(turn.content) // 3)
            for i in range(0, len(turn.content), step_len):
                chunk = turn.content[i:i + step_len]
                extracted = extractor.push(chunk)
                if extracted:
                    self.stream_callback("delta", extracted)

        return turn


def test_agent_runner_run_stream():
    """测试 AgentRunner.run_stream 生成器正常产出 stage, delta, done。"""
    answer_payload = {
        "replyType": "ANSWER",
        "answerText": "请重启路由器排查网络。",
        "usedVersionIds": [],
        "confidence": 0.95,
        "knowledgeConflict": False,
        "offTopic": False
    }
    raw_json = json.dumps(answer_payload, ensure_ascii=False)
    mock_turn = ModelTurn([], raw_json, None, ModelUsage(15, 20, 35, True))
    mock_client = MockStreamModelClient([mock_turn])

    governor = CostGovernor(
        router=ModelRouter(client=None),
        budget=TokenBudgetManager()
    )
    runner = AgentRunner(
        model_client=mock_client,
        mode="react",
        cost_governor=governor
    )

    req = AgentChatRequest(question="网络断开了怎么办？")
    events = list(runner.run_stream(req, user_id="U1001", role="ENGINEER", request_id="req-stream-001"))

    event_types = [e[0] for e in events]
    assert "stage" in event_types, "应包含 stage 阶段事件"
    assert "delta" in event_types, "应包含 delta 打字机流式增量事件"
    assert "done" in event_types, "应包含 done 结束事件"

    # 验证 delta 拼接结果
    deltas = [e[1]["delta"] for e in events if e[0] == "delta"]
    full_delta_text = "".join(deltas)
    assert full_delta_text == "请重启路由器排查网络。"

    # 验证 done 包含治理 Trace
    done_payload = next(e[1] for e in events if e[0] == "done")
    assert done_payload["replyType"] == "ANSWER"
    assert "governanceTrace" in done_payload
    trace = done_payload["governanceTrace"]
    assert trace["chosenTier"] in ["LITE", "STANDARD"]
    assert trace["chosenModel"] is not None


def test_fastapi_chat_stream_endpoint():
    """测试 /api/v1/agent/chat/stream HTTP 端点流式响应标准 SSE。"""
    answer_payload = {
        "replyType": "ANSWER",
        "answerText": "请检查工位网线接口连接是否稳固。",
        "usedVersionIds": [],
        "confidence": 0.9,
        "knowledgeConflict": False,
        "offTopic": False
    }
    raw_json = json.dumps(answer_payload, ensure_ascii=False)
    mock_turn = ModelTurn([], raw_json, None, ModelUsage(10, 15, 25, True))
    mock_client = MockStreamModelClient([mock_turn])

    governor = CostGovernor(
        router=ModelRouter(client=None),
        budget=TokenBudgetManager()
    )
    runner = AgentRunner(
        model_client=mock_client,
        mode="react",
        cost_governor=governor
    )
    app = create_app(runner=runner)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/agent/chat/stream",
        json={"question": "网口松了怎么办？"},
        headers={"X-User-Id": "U1002", "X-User-Role": "STAFF", "X-Request-Id": "req-sse-002"}
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    raw_body = resp.text
    assert "event: stage" in raw_body
    assert "event: delta" in raw_body
    assert "event: done" in raw_body
    assert "请检查工位网线接口连接是否稳固。" in raw_body


def test_streaming_answer_extractor_raw_markdown():
    """测试 StreamingAnswerExtractor 对纯 Markdown/文本流第一字符即时透传无 120 字符滞后。"""
    from agent_service.model_client import StreamingAnswerExtractor
    extractor = StreamingAnswerExtractor()

    # 第一个 chunk 仅有几个字符的 Markdown 标题
    chunk1 = "### 电脑"
    res1 = extractor.push(chunk1)
    assert res1 == "### 电脑", f"应首字即时流出，实际输出: {res1!r}"

    # 后续 chunk
    chunk2 = "运行缓慢排查"
    res2 = extractor.push(chunk2)
    assert res2 == "运行缓慢排查"


def test_streaming_answer_extractor_json_filtering():
    """测试 StreamingAnswerExtractor 对 Supervisor 内部意图 JSON 自动过滤，对 6 键 JSON 正确提取 answerText。"""
    from agent_service.model_client import StreamingAnswerExtractor

    # 1. 内部路由 JSON（不含 answerText）-> 应不产生任何 delta
    ext1 = StreamingAnswerExtractor()
    router_json = '{"needs_knowledge": true, "needs_ticket": false, "reason": "排障检索"}'
    out1 = ext1.push(router_json)
    assert out1 == "", "内部意图分类 JSON 不应泄露到前端 delta"

    # 2. 6 键标准响应 JSON -> 精准提取 answerText
    ext2 = StreamingAnswerExtractor()
    chunk_a = '{"replyType": "ANSWER", "answerText": "第一步：检查'
    chunk_b = '电源线连接\\n第二步：重启", "confidence": 0.95}'
    out_a = ext2.push(chunk_a)
    out_b = ext2.push(chunk_b)
    assert out_a == "第一步：检查"
    assert out_b == "电源线连接\n第二步：重启"

