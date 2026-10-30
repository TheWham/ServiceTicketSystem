# -*- coding: utf-8 -*-
"""动态节点池实体提取与对齐单元测试（废除硬编码词表）。"""

import pytest
from unittest.mock import MagicMock
from rag_pipeline.graph.reasoner import extract_query_entities


def test_extract_query_entities_with_dynamic_candidate_pool():
    """验证传入动态节点候选池时，无需任何硬编码常量即可精准识别实体。"""
    dynamic_pool = {
        "VPN错误691",
        "AD域账号锁定",
        "移动端邮件客户端旧密码轮询",
        "财务系统",
        "远程桌面(RDP)",
        "网络打印机",
        "VPN",  # 粗粒度
        "网络",  # 粗粒度
    }
    query = "在家连不上公司VPN，提示错误代码691认证失败，手机企业邮箱也凭据失效，是否是AD域账号锁定了？"

    entities = extract_query_entities(query, candidate_nodes=dynamic_pool)

    # 1. 必须命中具体的故障与系统节点
    assert "VPN错误691" in entities or "691" in "".join(entities)
    assert "AD域账号锁定" in entities

    # 2. 粗粒度剪枝生效：既然存在具体错误 691，纯泛化词 "VPN" 和 "网络" 应该被剪枝抑制
    assert "VPN" not in entities
    assert "网络" not in entities


def test_extract_query_entities_with_kg_mock():
    """验证从 Neo4jKnowledgeGraph 实例动态提取节点池并识别实体。"""
    mock_kg = MagicMock()
    mock_kg.get_all_node_names.return_value = {
        "共享文件夹访问被拒绝",
        "网络打印机",
        "Print Spooler",
        "ITKB-FILE-001",
    }

    query = "我的共享文件夹访问被拒绝，请查看 ITKB-FILE-001 处理办法"
    entities = extract_query_entities(query, kg=mock_kg)

    assert "共享文件夹访问被拒绝" in entities
    assert "ITKB-FILE-001" in entities
    assert mock_kg.get_all_node_names.called


def test_extract_query_entities_empty_fallback():
    """验证当既无候选池且 kg 为 None 时，能够安全返回卡片ID或空列表，不抛异常。"""
    query = "请问ITKB-VPN-001如何处理？"
    entities = extract_query_entities(query, candidate_nodes=set())
    assert "ITKB-VPN-001" in entities
