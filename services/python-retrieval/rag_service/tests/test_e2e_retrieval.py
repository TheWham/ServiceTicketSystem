# -*- coding: utf-8 -*-
"""全链路端到端集成测试：真实向量库 + MySQL Docstore 回溯 + API 契约校验。"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from rag_service.assembly import ServiceAssembly
from rag_service.app import create_app


@pytest.fixture(scope="module")
def real_client():
    sa = ServiceAssembly()
    app = create_app(assembly=sa)
    return TestClient(app)


def test_e2e_vpn_retrieval_with_mysql_docstore(real_client):
    """测试真实检索 '在家连不上VPN怎么办'：
    1. 命中子块（Chroma 向量 + BM25）；
    2. 父块正文从 MySQL rag_parent_docstore 批量拉取；
    3. 返回的 content 为完整 Markdown 父卡（长度 > 500），且 snippet 正常压缩。
    """
    resp = real_client.post("/api/v1/rag/retrievals", json={"question": "在家连不上VPN怎么办", "topK": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["msg"] == "success"

    data = body["data"]
    assert data["domain"] == "OFFICE_IT"
    assert data["reliable"] is True
    assert data["publishedOnly"] is True
    assert data["suggestedReplyType"] == "ANSWER"
    assert data.get("suggestedRefusalReason") is None

    items = data["items"]
    assert len(items) > 0
    assert len(items) <= 3

    top_item = items[0]
    assert "VPN" in top_item["title"]
    assert top_item["chunkId"].startswith("ITKB-VPN")
    # 核心验证：content 必须是从 MySQL Docstore 获取的整张父卡正文（> 500 字符，且包含 Markdown 结构）
    assert len(top_item["content"]) >= 500
    assert "##" in top_item["content"]
    assert len(top_item["snippet"]) <= 1000
    assert "\n" not in top_item["snippet"]


def test_e2e_low_confidence_refusal(real_client):
    """测试知识库完全未收录的无关对抗问题，必须被拒答且 items 为空。"""
    resp = real_client.post("/api/v1/rag/retrievals", json={"question": "明天午饭食堂吃红烧肉还是清蒸鲈鱼", "topK": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0

    data = body["data"]
    assert data["domain"] == "OFFICE_IT"
    assert data["reliable"] is False
    assert data["suggestedReplyType"] == "REFUSE"
    assert data["suggestedRefusalReason"] == "LOW_CONFIDENCE"
    assert data["items"] == []
