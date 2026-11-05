# -*- coding: utf-8 -*-
"""test_cost_governance.py

单元测试：Model Router 动态路由、Token 预算两阶段管控、自适应降档与全景调用链路 Trace。
"""
import pytest
from unittest.mock import MagicMock

from agent_service.cost_governance import (
    BudgetExceeded,
    CostGovernor,
    ModelProfile,
    ModelRouter,
    ModelTier,
    MODEL_CATALOG,
    TokenBudgetManager,
    estimate_cost,
    estimate_tokens,
)
from agent_service.model_client import ModelUsage
from agent_service.contract import AgentChatRequest, AgentChatResponse, GovernanceTrace
from agent_service.agent import AgentRunner


def test_token_and_cost_estimation():
    # 中文 10 汉字 + 英文/空格
    text = "公司访客WiFi密码是多少？"
    tokens = estimate_tokens(text)
    assert tokens > 0

    profile = MODEL_CATALOG[ModelTier.LITE]
    cost = estimate_cost(profile, 1000, 500)
    # 1000 * 0.0002 / 1000 + 500 * 0.0006 / 1000 = 0.0002 + 0.0003 = 0.0005
    assert abs(cost - 0.0005) < 1e-6


def test_model_router_heuristic_decisions():
    router = ModelRouter(client=None)

    # 1. 基础 FAQ -> LITE
    d1 = router.route("公司访客 WiFi 密码是多少？")
    assert d1.tier == ModelTier.LITE
    assert d1.min_tier == ModelTier.LITE
    assert d1.risk_level == "LOW"

    # 2. 方案对比 / 链路分析 -> STANDARD
    d2 = router.route("对比专线直连与异地 SSL-VPN 接入方案的架构差异与客户端配置")
    assert d2.tier == ModelTier.STANDARD
    assert d2.min_tier == ModelTier.LITE

    # 3. 生产高危 DROP / ALTER / 特批 -> PREMIUM + min_tier=STANDARD
    d3 = router.route("申请核心生产库 orders 表 DROP TABLE 高危特批提权")
    assert d3.tier == ModelTier.PREMIUM
    assert d3.min_tier == ModelTier.STANDARD
    assert d3.risk_level == "HIGH"


def test_token_budget_manager_two_phase():
    mgr = TokenBudgetManager(per_request_cap=5000, user_daily_limit=10000, dept_monthly_limit=50000)

    # 阶段一：预扣 2000
    mgr.reserve("req-001", "u1", "dept1", 2000)
    snap = mgr.snapshot("u1", "dept1")
    user_snap = next(v for k, v in snap.items() if "user:u1" in k)
    assert user_snap["reserved"] == 2000
    assert user_snap["available"] == 8000

    # 阶段二：结算 800，释放 1200 差额
    mgr.settle("req-001", 800)
    snap2 = mgr.snapshot("u1", "dept1")
    user_snap2 = next(v for k, v in snap2.items() if "user:u1" in k)
    assert user_snap2["reserved"] == 0
    assert user_snap2["used"] == 800
    assert user_snap2["available"] == 9200


def test_cost_governor_adaptive_degradation_and_circuit_breaker():
    # 用户日预算设置为 2000（不足以预扣 PREMIUM 的 3072 + prompt）
    mgr = TokenBudgetManager(user_daily_limit=2000)
    router = ModelRouter(client=None)
    governor = CostGovernor(router, mgr)

    # 对比类问题 (STANDARD 首选，需要 ~2560 + 输入 > 2000，降档至 LITE)
    plan = governor.plan("req-deg", "对比两种网络方案的区别", "u2", "dept2")
    assert plan.degraded is True
    assert plan.model.tier == ModelTier.LITE
    governor.budget.settle("req-deg", 300)

    # 高危问题 (PREMIUM 首选，min_tier 为 STANDARD，两者都超 2000 -> 触发 429 熔断拦截)
    with pytest.raises(BudgetExceeded) as exc_info:
        governor.plan("req-cb", "核心生产库提权 DROP TABLE 申请特批", "u3", "dept3")
    assert exc_info.value.is_circuit_breaker is True
    assert "安全熔断 429" in exc_info.value.detail


def test_cost_governor_build_trace():
    router = ModelRouter(client=None)
    mgr = TokenBudgetManager()
    governor = CostGovernor(router, mgr)

    plan = governor.plan("req-trace-1", "如何申请打印机驱动安装？", "u4", "dept4")
    trace_dict = governor.build_trace(plan, prompt_tokens=200, completion_tokens=150, latency_ms=650.0)

    assert trace_dict["traceId"] == "req-trace-1"
    assert trace_dict["chosenTier"] == "LITE"
    assert trace_dict["totalTokens"] == 350
    assert trace_dict["savingsRatePercent"] > 80.0  # LITE 较 PREMIUM 节省 80% 以上
    assert len(trace_dict["stages"]) == 5
    stage_ids = [s["stageId"] for s in trace_dict["stages"]]
    assert stage_ids == [
        "01_FEATURE_SCORING",
        "02_MODEL_ROUTING",
        "03_BUDGET_RESERVATION",
        "04_LLM_GENERATION",
        "05_COST_SETTLEMENT",
    ]


def test_agent_runner_governance_trace_integration():
    # 模拟 MockModelClient，返回合法 6 键 JSON
    mock_model = MagicMock()
    mock_turn = MagicMock()
    mock_turn.has_tool_calls = False
    mock_turn.content = '{"replyType": "ANSWER", "answerText": "请连接公司内部 WiFi：Corp-Guest，密码为 Welcome2026。", "usedVersionIds": [], "confidence": 0.95, "knowledgeConflict": false, "offTopic": false}'
    mock_turn.usage = ModelUsage(tokens_in=100, tokens_out=50, total_tokens=150, reported=True)
    mock_model.complete_with_tools.return_value = mock_turn
    mock_model.clone_with_model.return_value = mock_model
    mock_model.client = None

    runner = AgentRunner(model_client=mock_model, mode="react")
    req = AgentChatRequest(question="公司内部 WiFi 密码是什么？")
    resp = runner.run(req, user_id="U-EMP-01", role="EMPLOYEE", request_id="req-test-run")

    assert resp.reply_type == "ANSWER"
    assert "Welcome2026" in resp.answer_text
    assert resp.governance_trace is not None
    assert isinstance(resp.governance_trace, GovernanceTrace)
    assert resp.governance_trace.chosen_tier == "LITE"
    assert len(resp.governance_trace.stages) == 5
