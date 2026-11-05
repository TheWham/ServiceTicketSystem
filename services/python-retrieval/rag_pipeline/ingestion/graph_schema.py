# -*- coding: utf-8 -*-
"""图 schema 校验模块(Wiki 图知识库 阶段一 Task 1)。

纯函数校验,无 IO。后续任务(萃取器 / graph_builder / 前增补 runner)全部依赖本模块的
枚举常量、dataclass 与校验函数,是「元数据立得住,图才立得住」的第一道闸:

- 类型/枚举越界、名称为空、target 指向不存在编码 → ValueError(错误信息含字段路径
  与非法值,供调用方拼上卡名定位批次问题);
- 关系无证据(evidence 为 None/空串)→ 静默丢弃,这是防幻觉铁律的落点,不是可选项。

枚举值来自 spec(docs/superpowers/specs/2026-10-23-wiki-graph-knowledge-base-design.md),
变更须评估下游 Neo4j 图模型与检索扩展白名单。
"""

from dataclasses import dataclass
from typing import Any, List, Optional, Set

# spec 枚举逐字:实体类型 / 卡间关系类型 / 卡内结构节点 kind
ENTITY_TYPES = ("设备", "协议", "软件", "系统", "故障现象", "命令工具", "账号权限", "配置项", "概念")
RELATION_TYPES = ("replaces", "same_root_cause", "related", "process_applies")
NODE_KINDS = ("symptom", "root_cause", "tool")


@dataclass(frozen=True)
class EntityDef:
    name: str
    type: str


@dataclass(frozen=True)
class RelationDef:
    target: str
    type: str
    note: str
    evidence: Optional[str]


@dataclass(frozen=True)
class GraphNodeDef:
    kind: str
    name: str


def _require_str(raw: Any, where: str) -> str:
    """要求非空字符串(剥除首尾空白);否则 ValueError 含字段路径。"""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{where}: 期望非空字符串, 实得 {raw!r}")
    return raw.strip()


def validate_entities(raw: Any) -> List[EntityDef]:
    """校验类型化实体列表 ``[{name, type}]``。"""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"entities: 期望列表, 实得 {type(raw).__name__}")
    out: List[EntityDef] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"entities[{i}]: 期望对象, 实得 {type(item).__name__}")
        name = _require_str(item.get("name"), f"entities[{i}].name")
        type_ = item.get("type")
        if type_ not in ENTITY_TYPES:
            raise ValueError(
                f"entities[{i}].type: 非法类型 {type_!r} (合法: {'/'.join(ENTITY_TYPES)})"
            )
        out.append(EntityDef(name=name, type=type_))
    return out


def validate_relations(raw: Any, valid_targets: Set[str]) -> List[RelationDef]:
    """校验卡间关系列表 ``[{target, type, note, evidence}]``。

    - target 必须在 valid_targets(语料全部卡的编码集合)内,否则整批抛错
      (错误信息含该 target,便于批次定位——幻觉关系在源头即拒);
    - evidence 为 None(或空白)的关系**丢弃**,不产出条目。
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"relations: 期望列表, 实得 {type(raw).__name__}")
    out: List[RelationDef] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"relations[{i}]: 期望对象, 实得 {type(item).__name__}")
        target = _require_str(item.get("target"), f"relations[{i}].target")
        if target not in valid_targets:
            raise ValueError(
                f"relations[{i}].target: 未知目标 {target!r} "
                f"(不在语料 {len(valid_targets)} 张卡的编码集合内)"
            )
        type_ = item.get("type")
        if type_ not in RELATION_TYPES:
            raise ValueError(
                f"relations[{i}].type: 非法类型 {type_!r} (合法: {'/'.join(RELATION_TYPES)})"
            )
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            # 防幻觉铁律:给不出证据的关系不得进入产物。
            continue
        note = item.get("note")
        if note is None or not isinstance(note, str):
            note = note if isinstance(note, str) else ""
        out.append(RelationDef(target=target, type=type_, note=note, evidence=evidence))
    return out


def validate_graph_nodes(raw: Any) -> List[GraphNodeDef]:
    """校验卡内结构节点列表 ``[{kind, name}]``,kind 必须在 NODE_KINDS 内。"""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"graph_nodes: 期望列表, 实得 {type(raw).__name__}")
    out: List[GraphNodeDef] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"graph_nodes[{i}]: 期望对象, 实得 {type(item).__name__}")
        kind = item.get("kind")
        if kind not in NODE_KINDS:
            raise ValueError(
                f"graph_nodes[{i}].kind: 非法 kind {kind!r} (合法: {'/'.join(NODE_KINDS)})"
            )
        name = _require_str(item.get("name"), f"graph_nodes[{i}].name")
        out.append(GraphNodeDef(kind=kind, name=name))
    return out
