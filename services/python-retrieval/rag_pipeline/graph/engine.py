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
FACT_PATTERN = re.compile(r"^(?:【.+?】\s*)?(.+?)\s+──\((.+?)\)──>\s+(.+)$")


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
        self._cached_node_names: Optional[Set[str]] = None

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
        """初始化图数据库唯一约束与核心索引（采用标准中文标签体系 :实体）。"""
        with self.driver.session(database=self.database) as session:
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (e:实体) REQUIRE e.name IS UNIQUE"
            )
            session.run(
                "CREATE INDEX IF NOT EXISTS FOR (e:实体) ON (e.is_deprecated)"
            )

    def close(self) -> None:
        """安全释放驱动连接池。"""
        if hasattr(self, "driver") and self.driver:
            self.driver.close()

    def clear(self) -> None:
        """清空图谱全量数据（主要用于测试隔离与全量重建）。"""
        self._cached_node_names = None
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")

    def get_all_node_names(self, refresh: bool = False) -> Set[str]:
        """获取图谱中所有实体的唯一名称集合（带进程内缓存，彻底杜绝硬编码静态词库）。"""
        if self._cached_node_names is not None and not refresh:
            return self._cached_node_names

        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (e:实体) RETURN e.name AS name")
            self._cached_node_names = {record["name"] for record in result if record.get("name")}
            return self._cached_node_names

    def count_nodes(self) -> int:
        """统计实体节点总数。"""
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (e:实体) RETURN count(e) AS cnt")
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
            result = session.run("MATCH (e:实体 {is_deprecated: true}) RETURN count(e) AS cnt")
            record = result.single()
            return int(record["cnt"]) if record else 0

    def has_exact_node(self, name: str) -> bool:
        """精确检查指定字面名称的实体节点是否存在。"""
        with self.driver.session(database=self.database) as session:
            result = session.run(
                "MATCH (e:实体 {name: $name}) RETURN count(e) > 0 AS exists",
                name=name,
            )
            record = result.single()
            return bool(record["exists"]) if record else False

    def has_node(self, entity: str) -> bool:
        """检查实体是否在图谱中（支持自动别名消歧）。"""
        canon = canonicalize_entity(entity)
        return self.has_exact_node(canon)

    def add_triple(self, triple: GroundedTriple) -> None:
        """【链路一 · 步骤 4.4 幂等写入】add_triple(triple)
        
        输入：GroundedTriple 单条三元组对象（包含 head, relation, tail, evidence_quote）。
        动作：
          1. 实体消歧：利用 canonicalize_entity 对 head 和 tail 执行规范化别名统一；
          2. 废止打标：若 relation 为 REPLACES 或包含废止关键字，设置 is_deprecated=true 标记位；
          3. 原生 Cypher MERGE：
             MERGE (h:实体 {name: $head}) ... MERGE (t:实体 {name: $tail}) ... MERGE (h)-[r]->(t)
             保证节点与边写入时具备幂等性，重复灌库不产生多余节点与重边。
        返回：None。
        """
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
        MERGE (h:实体 {{name: $head}})
        ON CREATE SET h.is_deprecated = $dep_head
        ON MATCH SET h.is_deprecated = coalesce(h.is_deprecated, false) OR $dep_head
        MERGE (t:实体 {{name: $tail}})
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
        """【链路二 · 步骤 3.2 轨 A：图谱拓扑遍历与剪枝】extract_subgraph_facts(seed_entities, max_hops, prune_deprecated)
        
        输入：seed_entities（自然语言查询中提取的种子实体列表），max_hops（最大跳数，默认2）。
        动作：
          1. 种子归一化：通过 canonicalize_entity 标准化种子实体名并核验存在性；
          2. 执行 Neo4j 原生 Cypher 变长路径遍历：
             MATCH path = (seed:实体 {name: $seed})-[r*1..2]-(target:实体)
          3. 执行废弃版本物理剪枝：
             WHERE NONE(n IN nodes(path)[1..-1] WHERE coalesce(n.is_deprecated, false) = true)
             路径中只要途经已被废弃的旧制度/老卡片节点，整条后续路径立即截断！
          4. 格式化提取出的前向/反向关系及 evidence_quote 原文佐证。
        返回：格式化的事实字符串列表（如：'【因果事实】VPN错误691 ──(诱发根因)──> AD域账号锁定'）。
        """
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
        MATCH path = (seed:实体 {{name: $seed}})-[r*1..{max_hops}]-(target:实体)
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

        def _fact_sort_key(f_str: str) -> Tuple[int, int, str]:
            m = FACT_PATTERN.match(f_str.strip())
            if not m:
                return (9, 9, f_str)
            src_n, rel_n, dst_n = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            src_in = src_n in canonical_seeds
            dst_in = dst_n in canonical_seeds

            # Tier 0: 种子实体之间直接互联（如 VPN错误691 -> AD域账号锁定，移动端旧密码轮询 -> AD域账号锁定）
            if src_in and dst_in:
                return (0, 0, f_str)

            # Tier 1: 种子实体的处置动作与前置排查、制度废止
            if src_in or dst_in:
                if any(k in rel_n for k in ["排查", "处置", "动作", "等待", "重置"]):
                    return (1, 0, f_str)
                if any(k in rel_n for k in ["废止", "替代"]):
                    return (1, 1, f_str)
                if any(k in rel_n for k in ["根因", "诱发"]):
                    return (1, 2, f_str)
                if any(k in rel_n for k in ["主责", "通道", "系统", "组件"]):
                    return (1, 3, f_str)
                return (1, 4, f_str)

            # Tier 2: 2-Hop 间接外围边
            return (2, 0, f_str)

        matched_facts.sort(key=_fact_sort_key)
        return matched_facts

    def get_associated_card_ids(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        prune_deprecated: bool = True,
    ) -> List[str]:
        """【链路二 · 步骤 3.3 轨 B：顺藤摸瓜找父卡】get_associated_card_ids(seed_entities, max_hops, prune_deprecated)
        
        输入：seed_entities（种子实体列表）。
        动作：
          1. 沿种子实体执行 1~2 Hop Cypher 遍历并排除废弃节点；
          2. 使用正则 CARD_ID_PATTERN 匹配出路径中包含的所有知识卡片 ID（如 ITKB-VPN-001）；
          3. 去重排序，交由下游 MySQL Docstore 批量回溯拉取完整未切片父卡正文。
        返回：去重后的知识卡片编号列表（如 ['ITKB-ACC-001', 'ITKB-VPN-001']）。
        """
        canonical_seeds = [
            canonicalize_entity(e)
            for e in seed_entities
            if self.has_node(e)
        ]
        if not canonical_seeds:
            return []

        card_ids: Set[str] = set()

        cypher = f"""
        MATCH path = (seed:实体 {{name: $seed}})-[r*1..{max_hops}]-(target:实体)
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

    def extract_subgraph_data(
        self,
        seed_entities: List[str],
        max_hops: int = 2,
        prune_deprecated: bool = True,
        limit: int = 35,
    ) -> Dict[str, Any]:
        """从种子实体出发，提取结构化子图拓扑数据 (nodes & edges)，供前端画布高亮渲染。"""
        canonical_seeds = [
            canonicalize_entity(e)
            for e in seed_entities
            if self.has_node(e)
        ]
        if not canonical_seeds:
            return {"nodes": [], "edges": []}

        nodes_map: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []
        seen_edges: Set[Tuple[str, str, str]] = set()

        cypher = f"""
        MATCH path = (seed:实体 {{name: $seed}})-[r*1..{max_hops}]-(target:实体)
        WHERE NOT $prune OR (
            length(path) = 1
            OR NONE(n IN nodes(path)[1..-1] WHERE coalesce(n.is_deprecated, false) = true)
        )
        UNWIND range(0, length(path)-1) AS idx
        WITH relationships(path)[idx] AS rel
        RETURN DISTINCT
            startNode(rel).name AS src,
            coalesce(startNode(rel).is_deprecated, false) AS src_dep,
            type(rel) AS rel,
            endNode(rel).name AS dst,
            coalesce(endNode(rel).is_deprecated, false) AS dst_dep,
            coalesce(rel.quote, '') AS quote
        LIMIT $limit
        """

        with self.driver.session(database=self.database) as session:
            for seed in canonical_seeds:
                result = session.run(cypher, seed=seed, prune=prune_deprecated, limit=limit)
                for record in result:
                    src = record["src"]
                    rel = record["rel"]
                    dst = record["dst"]
                    src_dep = record["src_dep"]
                    dst_dep = record["dst_dep"]
                    quote = record["quote"]

                    edge_sig = (src, dst, rel)
                    if edge_sig not in seen_edges:
                        seen_edges.add(edge_sig)
                        if src not in nodes_map:
                            nodes_map[src] = {"id": src, "label": src, "is_deprecated": src_dep}
                        if dst not in nodes_map:
                            nodes_map[dst] = {"id": dst, "label": dst, "is_deprecated": dst_dep}
                        edges.append({
                            "from": src,
                            "to": dst,
                            "label": rel,
                            "title": quote or f"{src} ──({rel})──> {dst}",
                        })
                        if len(edges) >= limit:
                            break
                if len(edges) >= limit:
                    break

        return {"nodes": list(nodes_map.values()), "edges": edges}
