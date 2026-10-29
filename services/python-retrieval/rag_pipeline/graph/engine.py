# -*- coding: utf-8 -*-
"""基于 Neo4j 5 图数据库的生产级知识图谱拓扑计算引擎。

彻底取代基于 NetworkX 的轻量内存图实现。
支持连接池生命周期管理、实体消歧规范化、原生 Cypher 1~2 Hop 变长路径遍历与废弃版本拓扑剪枝。
遵循 AGENTS.md 约束：连接异常显式报错抛出，不执行静默降级或本地回退。
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import neo4j

from .schema import GroundedTriple, ITRelationEnum, canonicalize_entity

logger = logging.getLogger(__name__)

CARD_ID_PATTERN = re.compile(r"ITKB(?:-[A-Z0-9]+)+")


class Neo4jKnowledgeGraph:
    """生产级知识图谱引擎：基于 Neo4j 5 图数据库。"""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
    ) -> None:
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "neo4j123456")
        self.database = database

        try:
            self.driver = neo4j.GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=50,
            )
            self.driver.verify_connectivity()
            logger.info("Neo4j 图数据库连接成功: %s (db=%s)", self.uri, self.database)
        except Exception as e:
            msg = f"Neo4j 图数据库连接失败 [{self.uri}]: {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

        self._init_schema()

    def _init_schema(self) -> None:
        """初始化图数据库唯一约束与核心索引。"""
        with self.driver.session(database=self.database) as session:
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE"
            )
            session.run(
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.is_deprecated)"
            )

    def close(self) -> None:
        """安全释放驱动连接池。"""
        if hasattr(self, "driver") and self.driver:
            self.driver.close()

    def clear(self) -> None:
        """清空图谱全量数据（主要用于测试隔离与全量重建）。"""
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")

    def count_nodes(self) -> int:
        """统计实体节点总数。"""
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (e:Entity) RETURN count(e) AS cnt")
            record = result.single()
            return int(record["cnt"]) if record else 0

    def count_edges(self) -> int:
        """统计关系边总数。"""
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
            record = result.single()
            return int(record["cnt"]) if record else 0

    def count_deprecated_nodes(self) -> int:
        """统计标记废弃的节点总数。"""
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (e:Entity {is_deprecated: true}) RETURN count(e) AS cnt")
            record = result.single()
            return int(record["cnt"]) if record else 0

    def has_exact_node(self, name: str) -> bool:
        """精确检查指定字面名称的实体节点是否存在。"""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (e:Entity {name: $name}) RETURN count(e) > 0 AS exists",
                name=name,
            )
            record = result.single()
            return bool(record["exists"]) if record else False

    def has_node(self, entity: str) -> bool:
        """检查实体是否在图谱中（支持自动别名消歧）。"""
        canon = canonicalize_entity(entity)
        return self.has_exact_node(canon)

    def add_triple(self, triple: GroundedTriple) -> None:
        """向 Neo4j 添加单条三元组，自动执行消歧与废止识别。"""
        head = canonicalize_entity(triple.head)
        tail = canonicalize_entity(triple.tail)
        rel_val = (
            triple.relation.value
            if isinstance(triple.relation, ITRelationEnum)
            else str(triple.relation)
        )
        safe_rel = "".join([c for c in rel_val if c.isalnum() or c == "_"]) or "RELATED_TO"
        quote = triple.evidence_quote or ""

        dep_head = False
        dep_tail = False
        if rel_val == ITRelationEnum.REPLACES.value:
            dep_tail = True
        elif rel_val == ITRelationEnum.STATUS_IS.value and any(
            w in tail for w in ["废止", "废弃", "DEPRECATED", "下线"]
        ):
            dep_head = True

        cypher = f"""
        MERGE (h:Entity {{name: $head}})
        ON CREATE SET h.is_deprecated = $dep_head
        ON MATCH SET h.is_deprecated = coalesce(h.is_deprecated, false) OR $dep_head
        MERGE (t:Entity {{name: $tail}})
        ON CREATE SET t.is_deprecated = $dep_tail
        ON MATCH SET t.is_deprecated = coalesce(t.is_deprecated, false) OR $dep_tail
        MERGE (h)-[r:{safe_rel}]->(t)
        SET r.quote = $quote
        """
        with self.driver.session(database=self.database) as session:
            session.run(
                cypher,
                head=head,
                tail=tail,
                dep_head=dep_head,
                dep_tail=dep_tail,
                quote=quote,
            )

    def load_from_triples(self, triples: List[GroundedTriple], batch_size: int = 100) -> None:
        """批量载入三元组至 Neo4j。"""
        for i in range(0, len(triples), batch_size):
            chunk = triples[i : i + batch_size]
            for t in chunk:
                self.add_triple(t)

        logger.info(
            "Neo4j 图谱构建完毕: 节点数=%d, 边数=%d, 废弃节点数=%d",
            self.count_nodes(),
            self.count_edges(),
            self.count_deprecated_nodes(),
        )

    def extract_subgraph_facts(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        prune_deprecated: bool = True,
    ) -> List[str]:
        """从种子实体出发，执行 1~2 Hop Cypher 原生子图遍历，输出格式化事实。"""
        canonical_seeds = [
            canonicalize_entity(e)
            for e in seed_entities
            if self.has_node(e)
        ]
        if not canonical_seeds:
            return []

        matched_facts: List[str] = []
        seen_edges: Set[Tuple[str, str, str]] = set()

        cypher = f"""
        MATCH path = (seed:Entity {{name: $seed}})-[r*1..{max_hops}]-(target:Entity)
        WHERE NOT $prune OR (
            length(path) = 1
            OR NONE(n IN nodes(path)[1..-1] WHERE coalesce(n.is_deprecated, false) = true)
        )
        UNWIND range(0, length(path)-1) AS idx
        WITH nodes(path)[idx] AS u,
             nodes(path)[idx+1] AS v,
             relationships(path)[idx] AS rel
        RETURN DISTINCT
            startNode(rel).name AS src,
            type(rel) AS rel,
            endNode(rel).name AS dst,
            (startNode(rel) = u) AS is_forward,
            coalesce(rel.quote, '') AS quote
        """

        with self.driver.session(database=self.database) as session:
            for seed in canonical_seeds:
                result = session.run(cypher, seed=seed, prune=prune_deprecated)
                for record in result:
                    src = record["src"]
                    rel = record["rel"]
                    dst = record["dst"]
                    is_forward = record["is_forward"]

                    edge_sig = (src, dst, rel)
                    if edge_sig not in seen_edges:
                        seen_edges.add(edge_sig)
                        if is_forward:
                            fact = f"【因果事实】{src} ──({rel})──> {dst}"
                        else:
                            fact = f"【反向关联】{src} ──({rel})──> {dst}"
                        matched_facts.append(fact)

        return matched_facts

    def get_associated_card_ids(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        prune_deprecated: bool = True,
    ) -> List[str]:
        """从种子实体的子图中提取所有关联的有效 Wiki 卡片 ID（用于 MySQL Docstore 联动）。"""
        canonical_seeds = [
            canonicalize_entity(e)
            for e in seed_entities
            if self.has_node(e)
        ]
        if not canonical_seeds:
            return []

        card_ids: Set[str] = set()

        cypher = f"""
        MATCH path = (seed:Entity {{name: $seed}})-[r*1..{max_hops}]-(target:Entity)
        WHERE NOT $prune OR (
            length(path) = 1
            OR NONE(n IN nodes(path)[1..-1] WHERE coalesce(n.is_deprecated, false) = true)
        )
        UNWIND nodes(path) AS n
        RETURN DISTINCT n.name AS name, coalesce(n.is_deprecated, false) AS is_dep
        """

        with self.driver.session(database=self.database) as session:
            for seed in canonical_seeds:
                # 检查种子本身
                for cid in CARD_ID_PATTERN.findall(seed):
                    card_ids.add(cid)

                result = session.run(cypher, seed=seed, prune=prune_deprecated)
                for record in result:
                    name = record["name"]
                    is_dep = record["is_dep"]
                    if prune_deprecated and is_dep and name != seed:
                        continue
                    for cid in CARD_ID_PATTERN.findall(name):
                        card_ids.add(cid)

        return sorted(card_ids)
