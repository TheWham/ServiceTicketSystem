# -*- coding: utf-8 -*-
"""自适应检索内核集成测试：验证单维 vs 多维分流与图谱因果链切片无损融合。"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from rag_pipeline.graph.router import IntentAnalysisResult, QueryIntent
from rag_service.assembly import ServiceAssembly
from rag_service.app import create_app


@pytest.fixture(scope="module")
def real_assembly():
    return ServiceAssembly()


@pytest.fixture(scope="module")
def client(real_assembly):
    app = create_app(assembly=real_assembly)
    return TestClient(app)


def test_single_dimension_query_skips_graph(client, real_assembly):
    """测试单维查询：走纯双路召回，不执行图谱因果链前缀注入，契约字段合规。"""
    mock_single_intent = IntentAnalysisResult(
        intent=QueryIntent.SINGLE_DIMENSION,
        needs_graph=False,
        extracted_entities=["无线WiFi"],
        reason="单维配置查询",
    )

    with patch.object(real_assembly.router, "analyze", return_value=mock_single_intent):
        resp = client.post("/api/v1/rag/retrievals", json={"question": "如何连接公司访客WiFi？", "topK": 3})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0

        data = body["data"]
        assert data["domain"] == "OFFICE_IT"
        assert data["suggestedReplyType"] == "ANSWER"

        items = data["items"]
        assert len(items) > 0
        top_item = items[0]
        # 单维查询绝不包含图谱因果推导前缀
        assert "【知识图谱因果推导】" not in top_item["content"]
        assert top_item["articleId"] != "unknown"
        assert top_item["versionId"] != "unknown"


def test_multi_dimension_query_injects_graph_causal_chain(client, real_assembly):
    """测试复合关联查询：自动触发 GraphRAG，前置注入图谱因果推导链，且严格保持真实 articleId/versionId。"""
    mock_multi_intent = IntentAnalysisResult(
        intent=QueryIntent.MULTI_HOP_RELATIONAL,
        needs_graph=True,
        extracted_entities=["VPN错误691", "移动端邮件客户端旧密码轮询", "AD域账号锁定"],
        reason="跨系统复合因果故障",
    )

    with patch.object(real_assembly.router, "analyze", return_value=mock_multi_intent):
        query = "在家连不上公司VPN提示错误代码691认证失败，同时手机企业邮箱提示凭据失效"
        resp = client.post("/api/v1/rag/retrievals", json={"question": query, "topK": 3})
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0

        data = body["data"]
        assert data["domain"] == "OFFICE_IT"
        assert data["suggestedReplyType"] == "ANSWER"

        items = data["items"]
        assert len(items) > 0
        top_item = items[0]

        # 核心验证 1：首条切片已前置注入图谱因果推导
        assert "【知识图谱因果推导】" in top_item["content"]
        assert "诱发根因" in top_item["content"] or "AD域账号锁定" in top_item["content"]

        # 核心验证 2：确保 articleId 与 versionId 为知识库真实字段，不破坏 Java FOR SHARE NOWAIT 发布校验
        assert top_item["articleId"] != "unknown"
        assert top_item["versionId"] != "unknown"
        assert top_item["indexVersion"] == top_item["versionId"]
        assert top_item["score"] >= 0.0 and top_item["score"] <= 1.0
