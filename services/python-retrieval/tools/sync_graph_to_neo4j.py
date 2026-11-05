#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_graph_to_neo4j.py — graph_data.json 同步进本地 Neo4j(带标签全量重建)

Wiki 图知识库阶段二收官工具:把 Task 4 产物 `artifacts/output/graph/
graph_data.json` 灌进本地 Neo4j,供检索一跳图扩展(阶段三)查询。

设计要点(brief/spec 裁决逐字):
- **带标签重建**:全部节点统一附 `:ITKB` 标记标签,Card/Entity/Concept 再加
  第二标签与 kind 属性——重建首句逐字 `MATCH (n:ITKB) DETACH DELETE n`,
  只删 :ITKB 范围;共享 Neo4j 上绝不全局 DETACH DELETE,外部数据(探针、
  其他库)不允许被动到;
- **指纹幂等**:`(:ITKBGraphMeta {key:"applied", wiki_fingerprint})` 记录已
  同步指纹(该节点**不带** :ITKB,不在重建删除范围);指纹一致直接跳过,
  零写调用退出 0;
- **硬失败**:不可达/超时/计数不符 → 非零退出。无静默回退、不降级、不留
  半写状态(重建在单事务内,超时/中断整体回滚);
- REPLACES 边照常同步(它只是不进检索扩展白名单,那是 Task 8 的门);
- 本工具是离线运维工具,**不受 `graph.enabled` 开关限制**——enabled 只
  管检索热路径;凭证自取:环境变量(默认 NEO4J_PASSWORD)> RAG_HOME/.env
  同名键(复用 Task 8 load_config 解析),password 直填仅限本地测试且
  优先级最高。密码绝不进命令行与日志。

用法(在 services/python-retrieval 下,需已安装 neo4j>=5.0):
    python tools/sync_graph_to_neo4j.py
    python tools/sync_graph_to_neo4j.py --graph artifacts/output/graph/graph_data.json \
                                        --config configs/pipeline.yaml
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from neo4j import GraphDatabase, Query  # noqa: E402

from rag_pipeline.config import load_config  # noqa: E402

# 重建首句:逐字钉死(Review Focus 1),rag_service/tests/test_sync_graph.py
# 持续对账。改动这句 = 改删除范围,须过 spec 复核。
DELETE_ITKB = "MATCH (n:ITKB) DETACH DELETE n"

# 指纹 meta 节点:不带 :ITKB,因此重建永远删不到它
META_KEY = "applied"

# graph_data 节点 label → Neo4j 第二标签(首标签恒为 :ITKB)
NODE_SECONDARY_BY_LABEL = {"card": "Card", "entity": "Entity", "concept": "Concept"}

# 关系型只许大写字母开头的合法 Cypher 标识符(关系型进不了查询参数,
# 只能拼进语句文本——白名单外的形状一律显式拒绝,杜绝注入面)
_REL_TYPE_RE = re.compile(r"[A-Z][A-Z0-9_]*\Z")

# 重建事务超时(秒):bulk UNWIND 批量建 ~800 节点 / ~1000 边远重于热路径
# 单跳查询,取 timeout_ms(配置默认 300)的百倍量级即 30s;超时整体回滚,
# 不留半写状态。读查询(指纹/计数)仍走 timeout_ms 量级的单查询超时。
REBUILD_TX_TIMEOUT_S = 30.0

# 建库连接握手的等待上限(秒)
CONNECT_TIMEOUT_S = 5.0


class WritePlan(NamedTuple):
    """纯函数 build_write_plan 的产物:节点参数表 / 边参数表 / 指纹。

    NamedTuple 兼容 ``nodes, edges`` 语义,同时携带 wiki_fingerprint——
    apply 的 meta MERGE 与 CLI 的幂等判定都要用它。
    """

    nodes: List[Dict[str, Any]]       # {id, labels: ("ITKB", 第二标签), props}
    edges: List[Dict[str, Any]]      # {src, dst, type, props}
    wiki_fingerprint: str


class Counts(NamedTuple):
    """apply 落库计数(对账口径:plan 长度,verify_counts 随后按库复核)。"""

    nodes: int
    edges: int


def build_write_plan(graph_data: Dict[str, Any]) -> WritePlan:
    """graph_data.json → (节点参数表, 边参数表, wiki_fingerprint)。纯函数,无 IO。

    - 节点统一附标签 ``:ITKB``,Card/Entity/Concept 各加第二标签;
      Concept 的 ``kind`` 属性必须存在(缺 kind = 产物不合法,显式拒绝);
    - 节点 id 保持稳定(graph_builder 的 card:/entity:/concept: 编码),
      建边按 ``{id: …}`` MATCH,重复节点 id 显式拒绝(点名哪一条);
    - REPLACES 边照常进 plan(裁决:它只是不参与扩展白名单);
    - 越界输入(未知 label、非法关系型、空字段)一律 ValueError——同步
      工具不静默丢数据。
    """
    if not isinstance(graph_data, dict):
        raise ValueError(f"graph_data: 期望 dict, 实得 {type(graph_data).__name__}")

    fp = graph_data.get("wiki_fingerprint")
    if not isinstance(fp, str) or not fp.strip():
        raise ValueError(f"graph_data.wiki_fingerprint: 期望非空字符串, 实得 {fp!r}")

    nodes_raw = graph_data.get("nodes")
    edges_raw = graph_data.get("edges")
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
        raise ValueError("graph_data.nodes / graph_data.edges: 期望列表")

    nodes: List[Dict[str, Any]] = []
    seen_ids = set()
    for i, n in enumerate(nodes_raw):
        if not isinstance(n, dict):
            raise ValueError(f"nodes[{i}]: 期望对象, 实得 {type(n).__name__}")
        node_id = n.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError(f"nodes[{i}].id: 期望非空字符串, 实得 {node_id!r}")
        if node_id in seen_ids:
            raise ValueError(f"nodes[{i}].id: 重复节点 id {node_id!r}")
        seen_ids.add(node_id)
        label = n.get("label")
        if label not in NODE_SECONDARY_BY_LABEL:
            raise ValueError(
                f"nodes[{i}] ({node_id}): 未知 label {label!r} "
                f"(合法: {'/'.join(NODE_SECONDARY_BY_LABEL)})"
            )
        if label == "concept" and not str(n.get("kind", "")).strip():
            raise ValueError(f"nodes[{i}] ({node_id}): concept 节点缺 kind 属性")
        props = dict(n)
        props["id"] = node_id
        nodes.append({
            "id": node_id,
            "labels": ("ITKB", NODE_SECONDARY_BY_LABEL[label]),
            "props": props,
        })

    edges: List[Dict[str, Any]] = []
    for i, e in enumerate(edges_raw):
        if not isinstance(e, dict):
            raise ValueError(f"edges[{i}]: 期望对象, 实得 {type(e).__name__}")
        src, dst, rel_type = e.get("src"), e.get("dst"), e.get("type")
        for field in ("src", "dst"):
            if not isinstance(locals()[field], str) or not locals()[field].strip():
                raise ValueError(f"edges[{i}].{field}: 期望非空字符串, 实得 {e.get(field)!r}")
        if not isinstance(rel_type, str) or not _REL_TYPE_RE.fullmatch(rel_type):
            raise ValueError(
                f"edges[{i}].type: 非法关系型 {rel_type!r} "
                "(只许大写字母开头的标识符,如 MENTIONS/REPLACES)"
            )
        props = {k: v for k, v in e.items() if k not in ("src", "dst", "type")}
        edges.append({"src": src, "dst": dst, "type": rel_type, "props": props})

    return WritePlan(nodes=nodes, edges=edges, wiki_fingerprint=fp)


def _group_nodes(plan: WritePlan) -> List[Tuple[Tuple, List[Dict[str, Any]]]]:
    """按标签组合分组(插入序稳定,重建语句序确定可复盘)。"""
    groups: Dict[Tuple, List[Dict[str, Any]]] = {}
    for row in plan.nodes:
        groups.setdefault(tuple(row["labels"]), []).append({"props": row["props"]})
    return list(groups.items())


def _group_edges(plan: WritePlan) -> List[Tuple[str, List[Dict[str, Any]]]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in plan.edges:
        groups.setdefault(row["type"], []).append(
            {"src": row["src"], "dst": row["dst"], "props": row["props"]})
    return list(groups.items())


def apply(driver, plan: WritePlan, timeout_s: float = REBUILD_TX_TIMEOUT_S) -> Counts:
    """单事务执行带标签全量重建:删除 + 批量 CREATE 节点/边 + meta 指纹 MERGE。

    - 单个显式事务(``begin_transaction``):任一语句失败整体回滚,
      不留半写状态;事务级超时受 driver 支持(begin_transaction(timeout=…)),
      超时即由服务端终止事务;
    - 重建只删 :ITKB 范围(meta 节点不带 :ITKB,Person 等"外部"数据更不在内);
    - 删除是事务首句,在测试里逐字对账(Review Focus 1)。
    """
    with driver.session(database=None) as session:
        with session.begin_transaction(timeout=timeout_s) as tx:
            tx.run(DELETE_ITKB)  # 首句:重建范围只有 :ITKB
            for labels, rows in _group_nodes(plan):
                label_clause = ":".join(labels)
                tx.run(
                    f"UNWIND $rows AS row "
                    f"CREATE (n:{label_clause}) SET n = row.props",
                    rows=rows,
                )
            for rel_type, rows in _group_edges(plan):
                tx.run(
                    f"UNWIND $rows AS row "
                    f"MATCH (a:ITKB {{id: row.src}}), (b:ITKB {{id: row.dst}}) "
                    f"CREATE (a)-[r:{rel_type}]->(b) SET r = row.props",
                    rows=rows,
                )
            tx.run(
                "MERGE (m:ITKBGraphMeta {key: $key}) "
                "SET m.wiki_fingerprint = $fp",
                key=META_KEY, fp=plan.wiki_fingerprint,
            )
    return Counts(nodes=len(plan.nodes), edges=len(plan.edges))


def read_applied_fingerprint(driver, timeout_s: float) -> Optional[str]:
    """读库内已同步指纹;无 meta 节点 / 未同步 → None。"""
    cypher = ("MATCH (m:ITKBGraphMeta {key: $key}) "
              "RETURN m.wiki_fingerprint AS fp")
    with driver.session(database=None) as session:
        rec = session.run(Query(cypher, timeout=timeout_s),
                          key=META_KEY).single()
    return None if rec is None else rec["fp"]


def verify_counts(driver, plan: WritePlan, timeout_s: float = 5.0) -> None:
    """库内分型计数与 plan 对账,不符抛 ValueError(带全部差异明细)。

    对账口径:节点总数 + 各标签组合数 + 各关系型数(关系限定两端都是 :ITKB,
    声明同步范围,不误伤外部同名关系型)。
    """
    expected_rel = Counter(row["type"] for row in plan.edges)
    expected_node: Counter = Counter()
    for row in plan.nodes:
        expected_node[":".join(row["labels"])] += 1

    def db_count(session, cypher, **params) -> int:
        rec = session.run(Query(cypher, timeout=timeout_s), **params).single()
        return 0 if rec is None else rec["c"]

    mismatches: List[str] = []
    with driver.session(database=None) as session:
        total = db_count(session, "MATCH (n:ITKB) RETURN count(n) AS c")
        if total != len(plan.nodes):
            mismatches.append(
                f"节点总数: 库 {total} ≠ plan {len(plan.nodes)}")
        for label_clause, want in expected_node.items():
            got = db_count(
                session, f"MATCH (n:{label_clause}) RETURN count(n) AS c")
            if got != want:
                mismatches.append(f"{label_clause}: 库 {got} ≠ plan {want}")
        for rel_type, want in expected_rel.items():
            got = db_count(
                session,
                f"MATCH (a:ITKB)-[r:{rel_type}]->(b:ITKB) RETURN count(r) AS c")
            if got != want:
                mismatches.append(f"{rel_type}: 库 {got} ≠ plan {want}")

    if mismatches:
        raise ValueError("verify_counts 计数不符:\n  " + "\n  ".join(mismatches))


def _load_graph_data(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"graph_data 不存在: {path}(先跑 tools/enrich_wiki_metadata.py)")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"graph_data 解析失败({path}): {e}") from e


def _sync(args) -> int:
    cfg = load_config(str(REPO_ROOT / args.config))
    g = cfg.graph
    # 离线工具不受 graph.enabled 限制;但凭证必须就位——空密码绝不连库
    if not g.neo4j.password:
        raise ValueError(
            f"Neo4j 凭证为空:请设置环境变量 {g.neo4j.password_env}"
            f"(或 RAG_HOME/.env 同名键);本地测试可在配置 graph.neo4j.password 直填。"
        )
    graph_path = Path(args.graph)
    if not graph_path.is_absolute():
        graph_path = REPO_ROOT / graph_path
    graph_data = _load_graph_data(graph_path)
    plan = build_write_plan(graph_data)

    read_timeout_s = max(g.expansion.timeout_ms, 1000) / 1000.0
    print(f"🔗 Neo4j: {g.neo4j.uri}(用户 {g.neo4j.username})")
    print(f"📈 图数据: 节点 {len(plan.nodes)} / 边 {len(plan.edges)} / "
          f"指纹 {plan.wiki_fingerprint[:12]}…  ({graph_path.name})")

    driver = GraphDatabase.driver(
        g.neo4j.uri,
        auth=(g.neo4j.username, g.neo4j.password),
        connection_timeout=CONNECT_TIMEOUT_S,
    )
    try:
        driver.verify_connectivity()   # 不可达/凭证错在此显式爆,无静默回退
        applied = read_applied_fingerprint(driver, read_timeout_s)
        if applied == plan.wiki_fingerprint:
            print("✅ 指纹一致,跳过重建(幂等)")
            return 0
        if applied is not None:
            print(f"♻️  指纹变更 {applied[:12]}… → {plan.wiki_fingerprint[:12]}…,重建:ITKB 范围")
        else:
            print("🆕 库内无同步指纹,首次重建:ITKB 范围")
        counts = apply(driver, plan, timeout_s=REBUILD_TX_TIMEOUT_S)
        verify_counts(driver, plan, timeout_s=read_timeout_s)
        print(f"🎉 重建完成: 节点 {counts.nodes} / 边 {counts.edges},verify_counts 对账通过")
        return 0
    finally:
        driver.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wiki 图知识库 → Neo4j 带标签全量重建(指纹幂等/外部数据保护)")
    parser.add_argument("--graph", default="artifacts/output/graph/graph_data.json",
                        help="graph_data.json 路径(相对 services/python-retrieval)")
    parser.add_argument("--config", default="configs/pipeline.yaml",
                        help="pipeline.yaml 路径(取 graph.neo4j 连接参数)")
    args = parser.parse_args(argv)

    try:
        return _sync(args)
    except SystemExit:
        raise
    except Exception as e:      # noqa: BLE001
        # 统一硬失败出口:保留真实异常类型与原因,退出非零,绝不带病继续
        print(f"❌ 同步失败: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
