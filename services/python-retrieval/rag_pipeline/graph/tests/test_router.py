# -*- coding: utf-8 -*-
"""AdaptiveQueryRouter 单元测试与边界容错测试。"""

import json
from unittest.mock import MagicMock, patch
import pytest

from rag_pipeline.graph.router import (
    AdaptiveQueryRouter,
    IntentAnalysisResult,
    QueryIntent,
)


def test_router_single_dimension_mock():
    """测试单维事实/流程查询意图识别（Mock 返回）。"""
    router = AdaptiveQueryRouter(timeout=1.0)
    mock_llm_response = {
        "intent": "SINGLE_DIMENSION",
        "needs_graph": False,
        "extracted_entities": ["公司WiFi", "WiFi密码"],
        "reason": "用户仅询问单一无线网络密码，属于标准化SOP事实查询",
    }

    with patch.object(router, "_call_llm", return_value=json.dumps(mock_llm_response)):
        res = router.analyze("公司访客WiFi密码是多少？")
        assert res.intent == QueryIntent.SINGLE_DIMENSION
        assert res.needs_graph is False
        assert "公司WiFi" in res.extracted_entities
        assert "WiFi密码" in res.extracted_entities


def test_router_multi_hop_relational_mock():
    """测试多维复合故障与跨系统因果推导意图识别（Mock 返回）。"""
    router = AdaptiveQueryRouter(timeout=1.0)
    mock_llm_response = {
        "intent": "MULTI_HOP_RELATIONAL",
        "needs_graph": True,
        "extracted_entities": ["VPN错误691", "手机企业邮箱凭据失效", "AD域账号锁定"],
        "reason": "涉及跨系统（VPN与邮箱）协同故障，存在潜在因果关联",
    }

    with patch.object(router, "_call_llm", return_value=json.dumps(mock_llm_response)):
        query = "在家连不上VPN提示691认证失败，手机邮箱也凭据失效，是什么原因？"
        res = router.analyze(query)
        assert res.intent == QueryIntent.MULTI_HOP_RELATIONAL
        assert res.needs_graph is True
        assert "VPN错误691" in res.extracted_entities
        assert "AD域账号锁定" in res.extracted_entities


def test_router_timeout_or_error_graceful_fallback():
    """测试当外部模型调用超时或报错时，优雅兜底回落至 SINGLE_DIMENSION，不抛异常崩溃。"""
    router = AdaptiveQueryRouter(timeout=0.1)

    with patch.object(router, "_call_llm", side_effect=TimeoutError("Request timed out")):
        res = router.analyze("简单提问但网络挂了，打印机驱动怎么装")
        assert res.intent == QueryIntent.SINGLE_DIMENSION
        assert res.needs_graph is False
        assert "fallback" in res.reason


def test_router_timeout_rule_fallback_for_composite_fault():
    """测试外部模型调用超时时，命中复合多维故障特征安全回落为图谱推理，不遗漏因果链。"""
    router = AdaptiveQueryRouter(timeout=0.1)

    with patch.object(router, "_call_llm", side_effect=TimeoutError("Request timed out")):
        res = router.analyze("在家连不上公司VPN，提示错误代码691认证失败，今天早上手机企业邮箱也提示凭据失效")
        assert res.intent == QueryIntent.MULTI_HOP_RELATIONAL
        assert res.needs_graph is True
        assert "fallback_rule" in res.reason
        assert "VPN" in res.extracted_entities
        assert "错误代码691" in res.extracted_entities


def test_router_malformed_json_fallback():
    """测试大模型输出非标准 JSON 字符串时的健壮解析与容错。"""
    router = AdaptiveQueryRouter(timeout=1.0)

    # 包含 Markdown 标记包裹代码块
    markdown_wrapped = """```json
    {
        "intent": "MULTI_HOP_RELATIONAL",
        "needs_graph": true,
        "extracted_entities": ["远程桌面", "密码过期"],
        "reason": "多维排查"
    }
    ```"""
    with patch.object(router, "_call_llm", return_value=markdown_wrapped):
        res = router.analyze("远程桌面提示密码过期")
        assert res.intent == QueryIntent.MULTI_HOP_RELATIONAL
        assert res.needs_graph is True
        assert "远程桌面" in res.extracted_entities
