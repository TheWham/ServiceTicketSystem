# -*- coding: utf-8 -*-
"""glossary 与 graph_data 构建器(Wiki 图知识库 阶段一 Task 4)。

纯函数,无 LLM、无网络;IO 仅限显式传 path 的 load_glossary/save_glossary。
消费 Task 1 的校验器与 dataclass、Task 3 萃取产出并落进词表,产出阶段二
Neo4j 同步工具的唯一输入:`{wiki_fingerprint, glossary, nodes, edges}`。

节点 id 编码(计划逐字):`card:{wiki_id}` / `entity:{name}` / `concept:{kind}:{name}`。

边:
- `(card)-[:MENTIONS]->(entity)`:来自各卡类型化实体(证据 = 来源字段指认);
- `(card)-[:REPLACES|SAME_ROOT_CAUSE|RELATED|PROCESS_APPLIES]->(card)`:relations
  小写 type 映射大写,evidence 原样透传;
- `(concept)-[:SYMPTOM_OF|ROOT_CAUSE_OF|USED_IN]->(card)`:kind→边型映射
  symptom→SYMPTOM_OF / root_cause→ROOT_CAUSE_OF / tool→USED_IN。

REPLACES 对方向规约(controller 裁决,测试锁定):同一对卡双向产出 replaces 时,
只保 target 为 LEG 卡(源为现行卡)的那条——判定不靠猜测:
1. frontmatter status(status ∈ 已废止/已下线 → LEG;与流水线惯例一致,
   缺失视作现行)能唯一判定哪张是 LEG 卡 → 保留指向它的那条;
2. status 不可判定(两张同现行或同废止)→ 按 relations 条目的 evidence/note
   判定方向:note/evidence 自述「废止/下线/为准」的那条,其源卡即 LEG 卡,
   丢弃之,保留另一条;
3. 两者都无法判定(矛盾输入)→ 保留卡入参序列中先出现者为源的那条,并告警
   (矛盾不静默吞掉,但也不让整批因单对歧义硬失败——runner 批次可在人工
   门 Task 7 复核告警)。

边幂等去重:src/dst/type/evidence 四元组全等的重复边只保留一条(Task 1
裁决:重复项不去重属 Task 1 范围外;本构建器负责产出侧去重)。

先验后写:build_graph_data 内部先经 Task 1 validate_* 校验器(实体类型、关系
类型/target/证据、节点 kind),拒收即 ValueError,校验通过的数据才进产物。
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from .graph_schema import (
    EntityDef,
    validate_entities,
    validate_graph_nodes,
    validate_relations,
)

logger = logging.getLogger(__name__)

# 废止卡状态(与 configs/pipeline.yaml default_exclude、pipeline 里
# setdefault("wiki_status", "现行") 的既定约定一致)
LEG_STATUS = ("已废止", "已下线")
# status 无法判定时的 note/evidence 方向信号:自述「废止/下线/以…为准」
_NOTE_DEPRECATION_MARKERS = ("废止", "下线", "为准")

# relations.type(小写)→ 图边型(大写)
RELATION_EDGE_TYPES = {
    "replaces": "REPLACES",
    "same_root_cause": "SAME_ROOT_CAUSE",
    "related": "RELATED",
    "process_applies": "PROCESS_APPLIES",
}

# graph_nodes.kind → 概念边型
CONCEPT_EDGE_TYPES = {
    "symptom": "SYMPTOM_OF",
    "root_cause": "ROOT_CAUSE_OF",
    "tool": "USED_IN",
}

# 三类边的 evidence 来源指认(MENTIONS/概念边没有正文级证据,
# 指回产出它们的 frontmatter 字段,让同步层可解释边的出处)
ENTITIES_EVIDENCE = "frontmatter:entities"
GRAPH_NODES_EVIDENCE = "frontmatter:graph_nodes"

# Card 节点携带的镜像属性(Neo4j :Card 模型用,spec 54 行)
_CARD_NODE_FIELDS = ("wiki_id", "title", "category", "status", "version")


def card_node_id(wiki_id: str) -> str:
    return f"card:{wiki_id}"


def entity_node_id(name: str) -> str:
    return f"entity:{name}"


def concept_node_id(kind: str, name: str) -> str:
    return f"concept:{kind}:{name}"


def _is_leg_card(meta: Dict[str, Any]) -> bool:
    """status ∈ LEG_STATUS → LEG 卡;缺失/其他值 → 现行(流水线既定默认)。"""
    status = meta.get("status")
    return isinstance(status, str) and status in LEG_STATUS


# ---------- glossary:load / save / merge ----------


def load_glossary(path: Path) -> Dict[str, Any]:
    """读取实体词表;文件不存在 → `{"entities": {}}`(首跑建词表,不抛错)。

    文件存在但结构损坏 → ValueError(不静默重建,保住真实原因);
    词表是全局权威,重建等于把批次间对齐抹平。
    """
    if not Path(path).exists():
        return {"entities": {}}
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"glossary 顶层必须是对象, 实得 {type(raw).__name__}: {path}")
    entities = raw.get("entities")
    if not isinstance(entities, dict):
        raise ValueError(f"glossary.entities 必须是对象(名→{{type, aliases}}), 实得: {path}")
    for name, entry in entities.items():
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("type"), str)
            or not entry["type"].strip()
            or not isinstance(entry.get("aliases"), list)
        ):
            raise ValueError(
                f"glossary.entities[{name!r}] 损坏, 期望 {{type, aliases}}: {path}"
            )
    return {"entities": {name: dict(entry) for name, entry in entities.items()}}


def save_glossary(path: Path, glossary: Dict[str, Any]) -> None:
    """原子写词表(临时文件 + os.replace);写成可被 load_glossary 无损读到。"""
    path = Path(path)
    text = json.dumps(glossary, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = None, None
    try:
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise


def merge_new_entities(
    glossary: Dict[str, Any], new_entities: List[EntityDef]
) -> Dict[str, Any]:
    """幂等合并:词表已含的名称跳过(类型不被覆盖、不重复追加);

    新名称追加为 `{type, aliases: []}`。返回新 dict,入参不被改动。
    """
    # 先验后写:进词表的条目必须经 Task 1 校验器(类型枚举、名称非空)。
    validated = validate_entities(
        [{"name": e.name, "type": e.type} for e in new_entities]
    )
    out_entities = {name: dict(entry) for name, entry in glossary["entities"].items()}
    for e in validated:
        if e.name in out_entities:
            continue
        out_entities[e.name] = {"type": e.type, "aliases": []}
    return {"entities": out_entities}


# ---------- graph_data 组装 ----------


def _card_node(wiki_id: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    node: Dict[str, Any] = {"id": card_node_id(wiki_id), "label": "card"}
    for field in _CARD_NODE_FIELDS:
        value = wiki_id if field == "wiki_id" else meta.get(field)
        node[field] = value if isinstance(value, str) else ""
    return node


def _dedup_edges(edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """src/dst/type/evidence 四元组全等的边只保留先出现的一条。"""
    seen: Set[Tuple[str, str, str, str]] = set()
    out: List[Dict[str, Any]] = []
    for e in edges:
        key = (e["src"], e["dst"], e["type"], e["evidence"])
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _ordered_by_input(a: str, b: str, order: List[str]) -> Tuple[str, str]:
    """按卡入参序列把两个 wiki_id 排为 (先出现者, 后出现者)。"""
    ids = [a, b]
    return sorted(ids, key=lambda w: order.index(w))


def _dedupe_replaces_pairs(
    edges: List[Dict[str, Any]],
    metas: Dict[str, Dict[str, Any]],
    card_order: List[str],
) -> List[Dict[str, Any]]:
    """REPLACES 对方向规约(见模块 docstring 三级判定)。

    edges 内 REPLACES 边各带内部键 `_note`(relations 条目的 note),
    出口时剥离——产物边只含 src/dst/type/evidence 四键。
    """
    replacements: List[int] = [
        i for i, e in enumerate(edges) if e["type"] == "REPLACES"
    ]
    pair_indices: Dict[frozenset, List[int]] = {}
    for i in replacements:
        pair_indices.setdefault(frozenset((edges[i]["src"], edges[i]["dst"])), []).append(i)

    drop: Set[int] = set()
    for pair, idxs in pair_indices.items():
        if len(idxs) < 2:
            continue
        assert len(pair) == 2, f"REPLACES 边端点不是卡节点: {sorted(pair)}"
        first_id, second_id = _ordered_by_input(
            *(w[len("card:"):] for w in pair), order=card_order
        )
        legs = [w for w in (first_id, second_id) if _is_leg_card(metas[w])]

        keep_target: str  # card:{wiki_id}:保留 target 为 LEG 卡的那条
        if len(legs) == 1:
            keep_target = card_node_id(legs[0])
        else:
            # status 不可判定 → 按条目 note/evidence 判方向:
            # 自述「废止/下线/为准」的那条,源卡即 LEG 卡。
            carriers = {
                edges[i]["src"]
                for i in idxs
                if any(m in f"{edges[i].get('_note', '')}{edges[i]['evidence']}" for m in _NOTE_DEPRECATION_MARKERS)
            }
            if len(carriers) == 1:
                # carriers 中唯一源卡即 note/evidence 自述废止的 LEG 卡 → 保留指向它的那条
                keep_target = carriers.pop()
            else:
                # status 与 note/evidence 都无法判定(矛盾输入):
                # 保留输入序列中先出现者为源的那条,并告警供人工门复核。
                logger.warning(
                    "graph_builder: replaces 对 %s ↔ %s 双向产出且无法判定现行方向"
                    "(status 与前述 note/evidence 均无差异信号), 按卡输入顺序保留 %s → %s",
                    first_id, second_id, first_id, second_id,
                )
                keep_target = card_node_id(second_id)

        for i in idxs:
            if edges[i]["dst"] != keep_target:
                drop.add(i)

    return [
        {k: v for k, v in e.items() if k != "_note"}
        for i, e in enumerate(edges)
        if i not in drop
    ]


def build_graph_data(
    cards: List[Tuple[str, Dict[str, Any]]],
    glossary: Dict[str, Any],
    wiki_fingerprint: str,
) -> Dict[str, Any]:
    """组装 `{wiki_fingerprint, glossary, nodes, edges}`。

    cards = [(wiki_id, frontmatter dict)];frontmatter 仅消费
    entities(类型化)/relations/graph_nodes/status 及 Card 镜像属性,
    其余键零触碰。所有输入先经 Task 1 validate_* 校验器,拒收即
    ValueError——不把越界类型、幻觉 target 带进产物。
    """
    card_order: List[str] = [w for w, _ in cards]
    if len(set(card_order)) != len(card_order):
        dupes = sorted({w for w in card_order if card_order.count(w) > 1})
        raise ValueError(f"cards 含重复卡编码: {dupes}")
    metas: Dict[str, Dict[str, Any]] = dict(cards)
    valid_targets: Set[str] = set(card_order)

    glossary_types = {
        name: entry["type"] for name, entry in glossary["entities"].items()
    }

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    # 实体名 → 类型(首次提及顺序;词表类型优先,兜底卡上已验类型)
    entity_types: Dict[str, str] = {}

    for wiki_id, meta in cards:
        # 先验后写:三段 raw 全部过 Task 1 校验器。
        typed_entities = validate_entities(meta.get("entities"))
        relations = validate_relations(meta.get("relations"), valid_targets)
        graph_nodes = validate_graph_nodes(meta.get("graph_nodes"))

        nodes.append(_card_node(wiki_id, meta))
        src = card_node_id(wiki_id)
        for e in typed_entities:
            if e.name not in entity_types:
                entity_types[e.name] = glossary_types.get(e.name, e.type)
            edges.append(
                {"src": src, "dst": entity_node_id(e.name), "type": "MENTIONS",
                 "evidence": ENTITIES_EVIDENCE}
            )
        for r in relations:
            edges.append(
                {"src": src, "dst": card_node_id(r.target),
                 "type": RELATION_EDGE_TYPES[r.type], "evidence": r.evidence,
                 "_note": r.note}
            )
        for g in graph_nodes:
            edges.append(
                {"src": concept_node_id(g.kind, g.name), "dst": src,
                 "type": CONCEPT_EDGE_TYPES[g.kind],
                 "evidence": GRAPH_NODES_EVIDENCE}
            )

    # 实体/概念节点按首次提及顺序追加(确定性,与边顺序同源)。
    for name, type_ in entity_types.items():
        nodes.append({"id": entity_node_id(name), "label": "entity",
                      "name": name, "type": type_})
    seen_concepts: Set[Tuple[str, str]] = set()
    for _, meta in cards:
        for g in validate_graph_nodes(meta.get("graph_nodes")):
            if (g.kind, g.name) in seen_concepts:
                continue
            seen_concepts.add((g.kind, g.name))
            nodes.append({"id": concept_node_id(g.kind, g.name), "label": "concept",
                          "kind": g.kind, "name": g.name})

    # 实体类型汇总再过一次校验器:词表类型若越界,在这里硬拒。
    validate_entities([{"name": n, "type": t} for n, t in entity_types.items()])

    edges = _dedup_edges(edges)
    edges = _dedupe_replaces_pairs(edges, metas, card_order)

    return {
        "wiki_fingerprint": wiki_fingerprint,
        "glossary": {"entities": {n: dict(e) for n, e in glossary["entities"].items()}},
        "nodes": nodes,
        "edges": edges,
    }
