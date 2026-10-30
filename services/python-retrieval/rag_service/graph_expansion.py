# -*- coding: utf-8 -*-
"""一跳图扩展:沿 Neo4j 白名单边把命中卡(基础条目源卡)的邻居卡补进检索结果。

职责边界(Task 10,spec docs/superpowers/specs/2026-10-23-wiki-graph-knowledge-base-design.md):

- 扩展条目 = 父块代表内容 + 源卡 rerank_score × decay 的衰减分;
  绝不动基础条目原地,扩展分严格低于源(Task 8 已在加载期拒绝 decay≥1);
- REPLACES 边永不在扩展候选(Task 8 加载期拒绝其进白名单;本模块运行期
  对返回行仍做一次白名单复核,防线独立于查询文本);
- parents_by_id 缺该邻居(或父块内容为空)→ 跳过并计数,不崩;
- 已废止/已下线邻居不入;缺省(无 status 键或 status="")视为现行(裁决 20,
  真实图 frontmatter 无该键导致 status 为空串,正向等值会误杀):Cypher
  服务端否定式过滤 + python 侧按父块 metadata 的 wiki_status 复核(双防线);
  PUBLISHED 逐条生成前复核归 Java 准入谓词(Task 12),本模块不做生成侧复核;
- **没有静默回退**:图库不可达/图查询超时 → GraphUnavailable 硬失败,
  由 app.py 映射 HTTP 503 / code 5032,绝不把空结果假扮成"无邻居"。
"""

from typing import Any, Dict, List, Tuple

from neo4j import GraphDatabase, Query
from neo4j.exceptions import (
    AuthError,
    ConnectionAcquisitionTimeoutError,
    DatabaseError,
    DatabaseUnavailable,
    ReadServiceUnavailable,
    RoutingServiceUnavailable,
    ServiceUnavailable,
    SessionExpired,
    TransientError,
)

# 图库"不可用/超时"类失败:统一折叠为 GraphUnavailable 硬失败(503/5032)。
# 真实原因经 `raise … from` 保留在异常链里,不吞。查询文本/代码级缺陷
# (CypherSyntaxError 等 ClientError)不在此列——那是实现缺陷,原样外抛。
_AVAILABILITY_ERRORS: Tuple[type, ...] = (
    ServiceUnavailable,
    SessionExpired,
    AuthError,
    ConnectionAcquisitionTimeoutError,
    DatabaseError,
    DatabaseUnavailable,
    ReadServiceUnavailable,
    RoutingServiceUnavailable,
    TransientError,
    TimeoutError,
)

GRAPH_UNAVAILABLE_MSG: str = "图库不可用或图查询超时"    # 单一事实:模块内 raise 与 app.py 映射共用


# 邻居批查询(commit f5e0231e 校验脚本的 UNWIND 版,单批而非逐源 N 查):
#   - 无向匹配 (c)-[r]-(n):graph_builder 的 RELATED/PROCESS_APPLIES 指向方向
#     只反映声明顺序,扩展按"关系存在"理解,双向都算;
#   - 白名单 + 否定式现行过滤(NOT status IN ['已废止','已下线'],缺省
#     status="" 放行——LinuxSpoitBI 真实图 35/38 卡无 frontmatter status 键,
#     正向等值 n.status='现行' 会使扩展恒空,裁决 20 定为否定式)在服务端
#     过滤;按 n.wiki_id 排序保证截断确定性
#     (REPLACES 永不在白名单,Task 8 已拒绝其进 edge_whitelist);
#   - 返回列键名 = RETURN 表达式原文("id" / "n.wiki_id" / "type(r)"),逐字消费。
_CYPHER = (
    "UNWIND $ids AS id "
    "MATCH (c:Card {wiki_id: id})-[r]-(n:Card) "
    "WHERE type(r) IN $whitelist AND NOT n.status IN ['已废止','已下线'] "
    "RETURN id, n.wiki_id, type(r) "
    "ORDER BY n.wiki_id "
    "LIMIT $cap"
)

# 非现行状态的封闭集(裁决 20):不在此列的一律视为现行(含 status="" 缺省)。
_RETIRED_STATUSES = ("已废止", "已下线")

# 父块代表 metadata 里没有的字段一律不加;扩展键(Task 11 契约映射的内
# 部形态):graph_expanded / graph_expanded_from / graph_relation。
_K_EXPANDED = "graph_expanded"
_K_FROM = "graph_expanded_from"
_K_RELATION = "graph_relation"


class GraphUnavailable(RuntimeError):
    """图库不可用或图查询超时:硬失败,不静默回退为"无邻居"。

    app.py 将其映射为 HTTP 503、code 5032(依赖故障与检索空结果必须可区分)。
    """


class GraphExpander:
    """沿 Neo4j 一跳扩展命中卡,衰减分补条目;driver 懒构造、close 关闭。

    连接参数取自 rag_pipeline.config.GraphConfig(neo4j.uri/username/password,
    password 已在加载期从环境变量或 .env 解析;此处不再触碰环境)。
    """

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self._driver = None
        # 每次 expand 的跳过/产出计数(测试与排障都可读;不参与业务判定)
        self.last_stats: Dict[str, int] = {}

    # ---------------------------------------------------------------- 查询

    @property
    def _timeout_s(self) -> float:
        """单批查询的 Bolt 超时(配置毫秒折秒);计入共享预算。"""
        return self.cfg.expansion.timeout_ms / 1000.0

    def _ensure_driver(self):
        """懒构造 driver:false 开关下进程根本不建连;失败即硬失败。"""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self.cfg.neo4j.uri,
                    auth=(self.cfg.neo4j.username, self.cfg.neo4j.password),
                    connection_timeout=self._timeout_s,
                )
            except _AVAILABILITY_ERRORS as exc:
                raise GraphUnavailable(GRAPH_UNAVAILABLE_MSG) from exc
        return self._driver

    def expand(self, base_results: List[Dict[str, Any]],
               parents_by_id: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对基础检索结果做一跳扩展:返回**新增**条目列表(不就地改 base)。

        - 源卡 = base 的 parent 去重(首现序),衰减基分 = 该源首现 rerank_score;
        - 邻居经白名单/现行/缺父块三道门后按序截断至每源 max_neighbors;
        - 图库不可用/超时抛 GraphUnavailable,无任何静默回退路径。
        """
        sources: List[Tuple[str, float]] = []          # [(parent_id, rerank_score), 首现序]
        base_ids = set()
        for it in base_results:
            md = (it.get("metadata") or {})
            pid = md.get("parent_id") or md.get("wiki_id")
            if not pid or pid in base_ids:
                continue
            base_ids.add(pid)
            sources.append((str(pid), float(it["rerank_score"])))

        stats = {"rows": 0, "in_base": 0, "non_current": 0,
                 "missing_parent": 0, "entries": 0}
        self.last_stats = stats
        if not sources:
            return []                                  # 无源可扩展,不触碰图库

        exp = self.cfg.expansion
        query = Query(_CYPHER, timeout=self._timeout_s)
        try:
            driver = self._ensure_driver()
            with driver.session() as session:
                records = list(session.run(
                    query,
                    ids=[pid for pid, _ in sources],
                    whitelist=list(exp.edge_whitelist),
                    cap=len(sources) * exp.max_neighbors,
                ))
        except _AVAILABILITY_ERRORS as exc:
            raise GraphUnavailable(GRAPH_UNAVAILABLE_MSG) from exc
        stats["rows"] = len(records)

        # 白名单关系的返回行按源分组(行已按 n.wiki_id 全序)
        grouped: Dict[str, List[Tuple[str, str]]] = {}
        for rec in records:
            rel = rec["type(r)"]
            if rel not in exp.edge_whitelist:           # 运行期复核:REPLACES 等绝不过门
                continue
            grouped.setdefault(rec["id"], []).append((rec["n.wiki_id"], rel))

        new_entries: List[Dict[str, Any]] = []
        for src_id, src_score in sources:
            added = 0
            seen_neighbors = set()
            for nb_id, rel in grouped.get(src_id, []):
                if added >= exp.max_neighbors:
                    break
                if nb_id in base_ids:                   # 已是基础命中卡 → 不重复
                    stats["in_base"] += 1
                    continue
                if nb_id in seen_neighbors:             # 同邻居多条白名单边只取首条
                    continue
                parent = parents_by_id.get(nb_id)
                if not parent or not str(parent.get("parent_content") or "").strip():
                    stats["missing_parent"] += 1        # 缺父块/空正文 → 跳过并计数
                    continue
                if str(parent.get("wiki_status") or "现行") in _RETIRED_STATUSES:
                    stats["non_current"] += 1            # 已废止/已下线:python 侧复核;缺省=现行
                    continue
                seen_neighbors.add(nb_id)
                new_entries.append({
                    "content": parent["parent_content"],
                    "metadata": dict(parent),           # 父块代表:Task 11 从这里读三键
                    "rerank_score": round(src_score * exp.decay, 4),
                    _K_EXPANDED: True,
                    _K_FROM: src_id,
                    _K_RELATION: rel,
                })
                added += 1
        stats["entries"] = len(new_entries)
        return new_entries

    # ---------------------------------------------------------------- 生命周期

    def close(self) -> None:
        """显式关闭 Neo4j driver(app.py lifespan 退出时调用);幂等。"""
        driver, self._driver = self._driver, None
        if driver is not None:
            driver.close()
