# -*- coding: utf-8 -*-
"""GraphEnhancedReasoner 双轨融合推理单元测试。"""

import pytest
from rag_pipeline.docstore import InMemoryDocstore
from rag_pipeline.graph.schema import ITRelationEnum, GroundedTriple
from rag_pipeline.graph.engine import Neo4jKnowledgeGraph
from rag_pipeline.graph.reasoner import (
    extract_query_entities,
    GraphEnhancedReasoner,
)


@pytest.fixture(scope="module", autouse=True)
def restore_graph_after_reasoner_tests():
    yield
    from tools.sync_triples_to_neo4j import main as sync_neo4j_main
    sync_neo4j_main()


@pytest.fixture
def mock_reasoner() -> GraphEnhancedReasoner:
    kg = Neo4jKnowledgeGraph()
    kg.clear()
    triples = [
        GroundedTriple(
            head="VPN错误691",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="AD域账号锁定",
            evidence_quote="quote 1",
        ),
        GroundedTriple(
            head="ITKB-VPN-001",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="ITKB-ACC-001",
            evidence_quote="quote 2",
        ),
    ]
    kg.load_from_triples(triples)
    docstore = InMemoryDocstore({
        "ITKB-VPN-001": "# 【VPN-001】VPN连接排查全文...",
        "ITKB-ACC-001": "# 【ACC-001】域账号锁定排查全文...",
    })
    reasoner = GraphEnhancedReasoner(kg=kg, docstore=docstore, client=None)
    yield reasoner
    kg.clear()
    kg.close()


def test_extract_query_entities():
    query = "我在家连不上VPN，提示错误691认证失败，手机企业邮箱好像密码过期了"
    entities = extract_query_entities(query)
    assert any("VPN" in e for e in entities)
    assert any("691" in e for e in entities)


def test_retrieve_multihop_context(mock_reasoner: GraphEnhancedReasoner):
    ctx = mock_reasoner.retrieve_multihop_context(
        query="连不上VPN错误691",
        seed_entities=["VPN错误691", "ITKB-VPN-001"],
        max_hops=2,
    )
    # 验证图谱事实抽取
    assert len(ctx["graph_facts"]) >= 1
    assert any("AD域账号锁定" in f for f in ctx["graph_facts"])

    # 验证与 Docstore 联动拉取卡片全文
    assert "ITKB-VPN-001" in ctx["docstore_cards"]
    assert "ITKB-ACC-001" in ctx["docstore_cards"]
    assert "排查全文" in ctx["docstore_cards"]["ITKB-ACC-001"]


def test_build_hybrid_prompt(mock_reasoner: GraphEnhancedReasoner):
    ctx = mock_reasoner.retrieve_multihop_context(
        query="连不上VPN错误691",
        seed_entities=["VPN错误691", "ITKB-VPN-001"],
        max_hops=2,
    )
    prompt = mock_reasoner.build_hybrid_prompt("连不上VPN错误691", ctx)
    assert "【系统客观拓扑事实" in prompt
    assert "【关联知识库参考正文" in prompt
    assert "AD域账号锁定" in prompt
    assert "排查全文" in prompt
