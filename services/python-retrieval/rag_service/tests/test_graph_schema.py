# -*- coding: utf-8 -*-
"""图 schema 校验模块测试(Task 1)。

被测对象 rag_pipeline/ingestion/graph_schema.py 是后续全部图任务的依赖底座:
- 类型枚举常量 ENTITY_TYPES / RELATION_TYPES / NODE_KINDS(值 = spec 枚举逐字);
- dataclass EntityDef / RelationDef / GraphNodeDef;
- 校验函数 validate_entities / validate_relations / validate_graph_nodes。

铁律落点:关系无证据(evidence is None)即丢弃,不得进入产物;
target 不在合法编码集内则整批拒绝(ValueError),错误信息须含该 target 便于批次定位。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.ingestion.graph_schema import (  # noqa: E402
    ENTITY_TYPES,
    NODE_KINDS,
    RELATION_TYPES,
    EntityDef,
    GraphNodeDef,
    RelationDef,
    validate_entities,
    validate_graph_nodes,
    validate_relations,
)


def test_constants_match_spec():
    """枚举值必须与 spec 逐字一致——后续任务与 frontmatter 序列化都以此为准。"""
    assert ENTITY_TYPES == ("设备", "协议", "软件", "系统", "故障现象", "命令工具", "账号权限", "配置项", "概念")
    assert RELATION_TYPES == ("replaces", "same_root_cause", "related", "process_applies")
    assert NODE_KINDS == ("symptom", "root_cause", "tool")


def test_validate_entities_all_types_pass():
    """九种实体类型全部合法,一个不漏。"""
    raw = [{"name": f"实体{i}", "type": t} for i, t in enumerate(ENTITY_TYPES)]
    out = validate_entities(raw)
    assert out == [EntityDef(name=f"实体{i}", type=t) for i, t in enumerate(ENTITY_TYPES)]


def test_validate_entities_none_passes_as_empty():
    assert validate_entities(None) == []


def test_validate_entities_rejects_unknown_type():
    raw = [
        {"name": "VPN", "type": "协议"},
        {"name": "乱七八糟", "type": "不是类型"},
    ]
    with pytest.raises(ValueError) as ei:
        validate_entities(raw)
    msg = str(ei.value)
    assert "entities" in msg, "错误信息须含字段名便于定位"
    assert "不是类型" in msg, "错误信息须含非法值本身"


def test_validate_entities_rejects_empty_name():
    raw = [{"name": "   ", "type": "协议"}]
    with pytest.raises(ValueError, match="entities.*name"):
        validate_entities(raw)


def test_validate_entities_rejects_non_list_and_non_dict():
    with pytest.raises(ValueError):
        validate_entities("VPN")
    with pytest.raises(ValueError):
        validate_entities(["VPN"])


def test_validate_relations_all_types_pass():
    raw = [
        {"target": "ITKB-LEG-001", "type": t, "note": "备注", "evidence": f"证据-{t}"}
        for t in RELATION_TYPES
    ]
    out = validate_relations(raw, valid_targets={"ITKB-LEG-001"})
    assert out == [
        RelationDef(target="ITKB-LEG-001", type=t, note="备注", evidence=f"证据-{t}")
        for t in RELATION_TYPES
    ]


def test_validate_relations_unknown_target_rejected_whole_batch():
    """target 不在合法编码集:整批拒绝,错误信息含该 target(Review Focus 5)。"""
    raw = [
        {"target": "ITKB-NET-001", "type": "related", "note": "ok", "evidence": "e"},
        {"target": "ITKB-FAKE-999", "type": "replaces", "note": "幻觉", "evidence": "e"},
    ]
    with pytest.raises(ValueError) as ei:
        validate_relations(raw, valid_targets={"ITKB-NET-001"})
    assert "ITKB-FAKE-999" in str(ei.value), "错误信息须含未知 target 便于批次定位"


def test_validate_relations_none_passes_as_empty():
    assert validate_relations(None, valid_targets={"ITKB-A"}) == []


def test_validate_graph_nodes_none_passes_as_empty():
    assert validate_graph_nodes(None) == []


def test_validate_relations_drops_missing_evidence():
    """evidence is None 的关系被丢弃(防幻觉铁律),其余保留。"""
    raw = [
        {"target": "ITKB-A", "type": "related", "note": "有据", "evidence": "原文短句"},
        {"target": "ITKB-B", "type": "same_root_cause", "note": "无据", "evidence": None},
    ]
    out = validate_relations(raw, valid_targets={"ITKB-A", "ITKB-B"})
    assert out == [RelationDef(target="ITKB-A", type="related", note="有据", evidence="原文短句")]


def test_validate_relations_drops_blank_string_evidence():
    """锚定:evidence 为纯空白字符串与 None 同等丢弃;非空白证据原样保留、不剥空白。"""
    raw = [
        {"target": "ITKB-A", "type": "related", "note": "空白据", "evidence": "   "},
        {"target": "ITKB-B", "type": "related", "note": "实据", "evidence": "  证据原文  "},
    ]
    out = validate_relations(raw, valid_targets={"ITKB-A", "ITKB-B"})
    assert out == [RelationDef(target="ITKB-B", type="related", note="实据", evidence="  证据原文  ")]


def test_validate_relations_rejects_unknown_type():
    raw = [{"target": "ITKB-A", "type": "mentions", "note": "", "evidence": "e"}]
    with pytest.raises(ValueError, match="relations.*mentions"):
        validate_relations(raw, valid_targets={"ITKB-A"})


def test_validate_graph_nodes_all_kinds_pass():
    raw = [{"kind": k, "name": f"n-{k}"} for k in NODE_KINDS]
    out = validate_graph_nodes(raw)
    assert out == [GraphNodeDef(kind=k, name=f"n-{k}") for k in NODE_KINDS]


def test_validate_graph_nodes_rejects_unknown_kind():
    raw = [
        {"kind": "symptom", "name": "无法登录"},
        {"kind": "step", "name": "越界节点"},
    ]
    with pytest.raises(ValueError) as ei:
        validate_graph_nodes(raw)
    msg = str(ei.value)
    assert "graph_nodes" in msg and "step" in msg, "错误信息须含字段名与非法 kind"


def test_validate_graph_nodes_rejects_empty_name():
    raw = [{"kind": "tool", "name": ""}]
    with pytest.raises(ValueError, match="graph_nodes.*name"):
        validate_graph_nodes(raw)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
