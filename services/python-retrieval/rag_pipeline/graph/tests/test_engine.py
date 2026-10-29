# -*- coding: utf-8 -*-
import pytest
from rag_pipeline.graph.schema import ITRelationEnum, GroundedTriple
from rag_pipeline.graph.engine import LightKnowledgeGraph


@pytest.fixture
def sample_graph() -> LightKnowledgeGraph:
    triples = [
        # 故障链
        GroundedTriple(
            head="VPN错误691",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="AD域",
            evidence_quote="quote 1",
        ),
        GroundedTriple(
            head="AD域控制器",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="移动端邮件客户端旧密码轮询",
            evidence_quote="quote 2",
        ),
        GroundedTriple(
            head="移动端邮件客户端旧密码轮询",
            relation=ITRelationEnum.RESOLVED_BY,
            tail="退出手机端邮件重新登录",
            evidence_quote="quote 3",
        ),
        # 规约与废止链
        GroundedTriple(
            head="ITKB-ACC-001",
            relation=ITRelationEnum.REPLACES,
            tail="ITKB-LEG-ACC-001",
            evidence_quote="quote 4",
        ),
        GroundedTriple(
            head="ITKB-LEG-ACC-001",
            relation=ITRelationEnum.STATUS_IS,
            tail="已废止下线",
            evidence_quote="quote 5",
        ),
        GroundedTriple(
            head="ITKB-LEG-ACC-001",
            relation=ITRelationEnum.ROOT_CAUSE,
            tail="旧版永久锁定规则",
            evidence_quote="quote 6",
        ),
    ]
    kg = LightKnowledgeGraph()
    kg.load_from_triples(triples)
    return kg


def test_canonicalization_unifies_nodes(sample_graph: LightKnowledgeGraph):
    # 底层 NetworkX 节点的字面名应该被标准化为 "AD域控制器"，而原始字面 "AD域" 不应作为独立节点存在
    assert "AD域控制器" in sample_graph.graph.nodes
    assert "AD域" not in sample_graph.graph.nodes
    # 对外查询接口支持输入别名进行查找
    assert sample_graph.has_node("AD域")
    assert sample_graph.has_node("AD域控制器")


def test_multihop_bfs_traversal(sample_graph: LightKnowledgeGraph):
    # 从 VPN错误691 出发，1-Hop 应该只捞到 AD域控制器
    hop1_facts = sample_graph.extract_subgraph_facts(["VPN错误691"], max_hops=1)
    assert len(hop1_facts) == 1
    assert "AD域控制器" in hop1_facts[0]

    # 从 VPN错误691 出发，2-Hop 应该顺藤摸瓜捞到 移动端邮件客户端旧密码轮询
    hop2_facts = sample_graph.extract_subgraph_facts(["VPN错误691"], max_hops=2)
    assert len(hop2_facts) == 2
    fact_text = " ".join(hop2_facts)
    assert "VPN错误691" in fact_text
    assert "移动端邮件客户端旧密码轮询" in fact_text


def test_deprecated_pruning(sample_graph: LightKnowledgeGraph):
    # 当剪枝生效时，废弃节点 ITKB-LEG-ACC-001 的下级旧规则应该被剪掉
    facts = sample_graph.extract_subgraph_facts(["ITKB-ACC-001"], max_hops=2, prune_deprecated=True)
    fact_text = " ".join(facts)
    assert "ITKB-LEG-ACC-001" in fact_text
    assert "旧版永久锁定规则" not in fact_text
