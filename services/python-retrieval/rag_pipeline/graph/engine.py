# -*- coding: utf-8 -*-
"""基于 NetworkX 的轻量级内存图拓扑计算引擎。

支持有向多重图 (MultiDiGraph)、实体消歧、1~2 Hop BFS 子图遍历与废弃版本拓扑剪枝。
"""

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from .schema import GroundedTriple, ITRelationEnum, canonicalize_entity

logger = logging.getLogger(__name__)

CARD_ID_PATTERN = re.compile(r"ITKB(?:-[A-Z0-9]+)+")


class LightKnowledgeGraph:
    """生产级轻量知识图谱引擎：基于 NetworkX 内存有向多重图。"""

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()
        self.deprecated_nodes: Set[str] = set()

    def has_node(self, entity: str) -> bool:
        """检查实体是否在图谱中（支持自动消歧）。"""
        canon = canonicalize_entity(entity)
        return self.graph.has_node(canon)

    def add_triple(self, triple: GroundedTriple) -> None:
        """向图谱添加单条三元组，自动执行实体消歧与废止识别。"""
        head = canonicalize_entity(triple.head)
        tail = canonicalize_entity(triple.tail)
        relation_val = (
            triple.relation.value
            if isinstance(triple.relation, ITRelationEnum)
            else str(triple.relation)
        )

        # 识别废止节点（便于后续剪枝）
        if triple.relation == ITRelationEnum.REPLACES:
            self.deprecated_nodes.add(tail)
        elif triple.relation == ITRelationEnum.STATUS_IS and any(
            w in tail for w in ["废止", "废弃", "DEPRECATED", "下线"]
        ):
            self.deprecated_nodes.add(head)

        self.graph.add_edge(
            head,
            tail,
            relation=relation_val,
            quote=triple.evidence_quote,
        )

    def load_from_triples(self, triples: List[GroundedTriple]) -> None:
        """批量载入三元组。"""
        for t in triples:
            self.add_triple(t)
        logger.info(
            "图谱构建完毕: 节点数=%d, 边数=%d, 废弃节点数=%d",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
            len(self.deprecated_nodes),
        )

    def extract_subgraph_facts(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        prune_deprecated: bool = True,
    ) -> List[str]:
        """从种子实体出发，执行 1~2 Hop 广度优先 (BFS) 子图遍历，输出格式化事实。"""
        matched_facts: List[str] = []
        visited_nodes: Set[str] = set()
        seen_edges: Set[Tuple[str, str, str]] = set()

        canonical_seeds = [
            canonicalize_entity(e)
            for e in seed_entities
            if self.has_node(e)
        ]
        if not canonical_seeds:
            return []

        for seed in canonical_seeds:
            current_layer = {seed}
            visited_nodes.add(seed)

            for _ in range(max_hops):
                next_layer: Set[str] = set()
                for u in current_layer:
                    # 如果该节点是已废止节点且开启剪枝，不再向下漫延展开
                    if prune_deprecated and u in self.deprecated_nodes and u != seed:
                        continue

                    # 1. 遍历正向出边 (u -> v)
                    for _, v, edge_data in self.graph.out_edges(u, data=True):
                        rel = edge_data.get("relation", "关联")
                        edge_sig = (u, v, rel)
                        if edge_sig not in seen_edges:
                            seen_edges.add(edge_sig)
                            fact = f"【因果事实】{u} ──({rel})──> {v}"
                            matched_facts.append(fact)

                        # 如果 v 是废止节点且开启剪枝，收集边后不再将 v 放入 next_layer
                        if prune_deprecated and v in self.deprecated_nodes:
                            visited_nodes.add(v)
                            continue

                        if v not in visited_nodes:
                            next_layer.add(v)
                            visited_nodes.add(v)

                    # 2. 遍历反向入边 (v -> u)
                    for v, _, edge_data in self.graph.in_edges(u, data=True):
                        rel = edge_data.get("relation", "关联")
                        # 如果该边已经作为 (v -> u) 记录过，不再以反向格式重复打印
                        edge_sig = (v, u, rel)
                        if edge_sig not in seen_edges:
                            seen_edges.add(edge_sig)
                            fact = f"【反向关联】{v} ──({rel})──> {u}"
                            matched_facts.append(fact)

                        if prune_deprecated and v in self.deprecated_nodes:
                            visited_nodes.add(v)
                            continue

                        if v not in visited_nodes:
                            next_layer.add(v)
                            visited_nodes.add(v)

                current_layer = next_layer

        return matched_facts

    def get_associated_card_ids(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        prune_deprecated: bool = True,
    ) -> List[str]:
        """从种子实体的子图中提取所有关联的有效 Wiki 卡片 ID（用于 MySQL Docstore 联动）。"""
        card_ids: Set[str] = set()
        canonical_seeds = [canonicalize_entity(e) for e in seed_entities if self.has_node(e)]

        for seed in canonical_seeds:
            current_layer = {seed}
            visited = {seed}

            # 检查种子本身
            for cid in CARD_ID_PATTERN.findall(seed):
                if not (prune_deprecated and cid in self.deprecated_nodes):
                    card_ids.add(cid)

            for _ in range(max_hops):
                next_layer: Set[str] = set()
                for u in current_layer:
                    if prune_deprecated and u in self.deprecated_nodes and u != seed:
                        continue

                    for _, v, _ in self.graph.out_edges(u, data=True):
                        for cid in CARD_ID_PATTERN.findall(v):
                            if not (prune_deprecated and cid in self.deprecated_nodes):
                                card_ids.add(cid)
                        if v not in visited:
                            visited.add(v)
                            if not (prune_deprecated and v in self.deprecated_nodes):
                                next_layer.add(v)

                    for v, _, _ in self.graph.in_edges(u, data=True):
                        for cid in CARD_ID_PATTERN.findall(v):
                            if not (prune_deprecated and cid in self.deprecated_nodes):
                                card_ids.add(cid)
                        if v not in visited:
                            visited.add(v)
                            if not (prune_deprecated and v in self.deprecated_nodes):
                                next_layer.add(v)

                current_layer = next_layer

        return sorted(card_ids)
