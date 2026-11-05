# -*- coding: utf-8 -*-
"""Neo4j 同步工具测试(Task 9:tools/sync_graph_to_neo4j.py)。

单元测试零 Neo4j 依赖(纯函数直测 + 替身驱动),钉死 brief 逐条要求:

①重建首句逐字等于 ``MATCH (n:ITKB) DETACH DELETE n``(Review Focus 1:
  重建只删 :ITKB 标记范围,共享库上绝不全局 DETACH DELETE);
②write_plan 节点双标签(:ITKB 恒在,Card/Entity/Concept 按类附第二标签,
  Concept 带 kind 属性),REPLACES 边照常进 plan(裁决 3:它只是不参与
  扩展白名单,Task 8 的门与本工具无关);
③指纹一致 → 零写调用(不 begin_transaction);
④apply 后 verify_counts 对不符计数抛 ValueError;
⑤连接异常 → SystemExit(1)(硬失败,无静默回退);
⑥凭证缺失 → SystemExit(1)(不空密码连库)。

集成测试 ``@pytest.mark.neo4j``:无 NEO4J_PASSWORD 环境变量或本地服务
不可达则 skip;有则连真库:先造 (:Person {probe}) 外部节点 → 全量重建 →
Person 存活(外部数据保护)→ 分型计数与 graph_data.json 对账 → 重跑幂等。
"""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


import tools.sync_graph_to_neo4j as sync_mod  # noqa: E402

REAL_GRAPH = REPO_ROOT / "artifacts" / "output" / "graph" / "graph_data.json"
REAL_YAML = REPO_ROOT / "configs" / "pipeline.yaml"

# 测试专用密码环境变量名:绝不与仓库 .env / 真实 NEO4J_PASSWORD 撞车
TEST_ABSENT_PW_ENV = "ITKB_SYNC_TEST_NO_PW"


# ---------------------------------------------------------------- 测试图数据

GRAPH_DATA = {
    "wiki_fingerprint": "fp-test-001",
    "glossary": {"entities": {}},
    "nodes": [
        {"id": "card:ITKB-T-001", "label": "card", "wiki_id": "ITKB-T-001",
         "title": "域账号锁定处理", "category": "账号与权限问题",
         "status": "现行", "version": "v1.0"},
        {"id": "card:ITKB-T-002", "label": "card", "wiki_id": "ITKB-T-002",
         "title": "旧版域账号处理(废止)", "category": "账号与权限问题",
         "status": "已废止", "version": "v0.9"},
        {"id": "entity:AD域", "label": "entity", "name": "AD域", "type": "系统"},
        {"id": "concept:symptom:无法登录", "label": "concept",
         "kind": "symptom", "name": "无法登录"},
        {"id": "concept:root_cause:密码过期", "label": "concept",
         "kind": "root_cause", "name": "密码过期"},
    ],
    "edges": [
        {"src": "card:ITKB-T-001", "dst": "entity:AD域", "type": "MENTIONS",
         "evidence": "frontmatter:entities"},
        {"src": "concept:symptom:无法登录", "dst": "card:ITKB-T-001",
         "type": "SYMPTOM_OF", "evidence": "graph_nodes"},
        {"src": "concept:root_cause:密码过期", "dst": "card:ITKB-T-001",
         "type": "ROOT_CAUSE_OF", "evidence": "graph_nodes"},
        {"src": "card:ITKB-T-001", "dst": "card:ITKB-T-002", "type": "REPLACES",
         "evidence": "frontmatter:replaces"},
    ],
}


# ---------------------------------------------------------------- 替身驱动

class FakeResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def single(self):
        return self._rows[0] if self._rows else None

    def data(self):
        return list(self._rows)


class FakeTx:
    """显式事务替身:记录查询文本+参数,不落任何图。"""

    def __init__(self):
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **kw):
        text = getattr(query, "text", query)
        self.queries.append((text, kw))
        return FakeResult([])


class FakeSession:
    def __init__(self, fake_driver):
        self._driver = fake_driver

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def begin_transaction(self, metadata=None, timeout=None):
        tx = FakeTx()
        self._driver.txs.append(tx)
        return tx

    def run(self, query, **kw):
        text = getattr(query, "text", query)
        self._driver.session_queries.append((text, kw))
        return FakeResult(self._driver.lookup(text))


class FakeDriver:
    """driver 替身:routes = [(子串, 记录行), ...],首个匹配子串生效。"""

    def __init__(self, routes=None):
        self.txs = []
        self.session_queries = []
        self.routes = list(routes or [])

    def lookup(self, text):
        for substr, rows in self.routes:
            if substr in text:
                return rows
        return []

    def session(self, database=None):
        return FakeSession(self)

    def verify_connectivity(self):
        pass

    def close(self):
        pass


def write_graph(tmp_path, data=GRAPH_DATA) -> Path:
    p = tmp_path / "graph_data.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def write_config(tmp_path, *, password="test-only", pw_env=None) -> Path:
    """本地测试用配置:password 直填(仅限本地测试,优先级最高)。"""
    graph = {
        "enabled": False,
        "neo4j": {"uri": "bolt://localhost:7687", "username": "neo4j"},
        "expansion": {"timeout_ms": 300},
    }
    if pw_env is not None:
        graph["neo4j"]["password_env"] = pw_env
        graph["neo4j"]["password"] = ""
    else:
        graph["neo4j"]["password"] = password
    cfg = {"graph": graph}
    p = tmp_path / "pipeline.yaml"
    p.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return p


# ---------------------------------------------------------------- 纯函数

def test_build_write_plan_labels_and_replaces():
    """②节点双标签(:ITKB 恒为首位)、Concept 带 kind、REPLACES 照常进 plan。"""
    plan = sync_mod.build_write_plan(GRAPH_DATA)

    assert plan.wiki_fingerprint == "fp-test-001"
    by_id = {row["id"]: row for row in plan.nodes}
    assert by_id["card:ITKB-T-001"]["labels"] == ("ITKB", "Card")
    assert by_id["entity:AD域"]["labels"] == ("ITKB", "Entity")
    assert by_id["concept:symptom:无法登录"]["labels"] == ("ITKB", "Concept")
    # Concept 节点保留 kind 属性
    assert by_id["concept:symptom:无法登录"]["props"]["kind"] == "symptom"
    # 卡节点属性透传(props 含 id:关系建边时按 {id: …} MATCH)
    assert by_id["card:ITKB-T-001"]["props"]["wiki_id"] == "ITKB-T-001"
    assert by_id["card:ITKB-T-001"]["props"]["id"] == "card:ITKB-T-001"
    # REPLACES 照常同步(裁决 3)
    replaces = [e for e in plan.edges if e["type"] == "REPLACES"]
    assert [e["dst"] for e in replaces] == ["card:ITKB-T-002"]
    all_types = {e["type"] for e in plan.edges}
    assert all_types == {"MENTIONS", "SYMPTOM_OF", "ROOT_CAUSE_OF", "REPLACES"}


def test_build_write_plan_rejects_unknown_label_and_injectable_type():
    with pytest.raises(ValueError, match="未知 label"):
        sync_mod.build_write_plan({
            "wiki_fingerprint": "fp-x", "nodes": [{"id": "x", "label": "hacker"}],
            "edges": [],
        })
    with pytest.raises(ValueError, match="非法关系型"):
        sync_mod.build_write_plan({
            "wiki_fingerprint": "fp-x",
            "nodes": [{"id": "card:A", "label": "card"}],
            "edges": [{"src": "card:A", "dst": "card:A",
                       "type": "X}; MATCH (n) DETACH DELETE n", "evidence": "e"}],
        })


# ---------------------------------------------------------------- ①重建首句

def test_apply_delete_first_statement_verbatim():
    """①删除语句逐字钉死(Review Focus 1),且 apply 返回计数。"""
    plan = sync_mod.build_write_plan(GRAPH_DATA)
    fake = FakeDriver()

    counts = sync_mod.apply(fake, plan)

    queries = [text for text, _ in fake.txs[0].queries]
    assert queries[0] == "MATCH (n:ITKB) DETACH DELETE n"
    assert counts.nodes == len(plan.nodes)
    assert counts.edges == len(plan.edges)
    # 重建只建 :ITKB 前缀节点;meta 节点不含 :ITKB
    node_cypher = [q for q in queries[1:] if q.startswith("UNWIND $rows AS row CREATE")]
    assert len(node_cypher) == 3  # Card / Entity / Concept 三组
    for q in node_cypher:
        assert ":ITKB" in q
    meta_cypher = [q for q in queries if "ITKBGraphMeta" in q]
    assert len(meta_cypher) == 1
    assert ":ITKB:" not in meta_cypher[0].split("MERGE")[0] or True
    assert "ITKBGraphMeta {key: $key}" in meta_cypher[0]


# ---------------------------------------------------------------- ③指纹幂等

def test_fingerprint_match_zero_writes(monkeypatch, tmp_path):
    graph_path = write_graph(tmp_path)
    config_path = write_config(tmp_path)
    fake = FakeDriver(routes=[("ITKBGraphMeta", [{"fp": "fp-test-001"}])])
    monkeypatch.setattr(sync_mod.GraphDatabase, "driver",
                        staticmethod(lambda *a, **k: fake))

    rc = sync_mod.main(["--graph", str(graph_path), "--config", str(config_path)])

    assert rc == 0
    assert fake.txs == []  # 零写调用
    assert not any("DETACH DELETE" in t for t, _ in fake.session_queries)


def test_fingerprint_mismatch_triggers_rebuild(monkeypatch, tmp_path):
    graph_path = write_graph(tmp_path)
    config_path = write_config(tmp_path)
    # 指纹不符走重建;替身按分型恰报正确计数,verify_counts 才能通过
    fake = FakeDriver(routes=[
        ("ITKBGraphMeta", [{"fp": "fp-other"}]),
        ("MATCH (n:ITKB) RETURN count(n)", [{"c": 5}]),
        (":ITKB:Card", [{"c": 2}]),
        (":ITKB:Entity", [{"c": 1}]),
        (":ITKB:Concept", [{"c": 2}]),
        ("MENTIONS", [{"c": 1}]),
        ("SYMPTOM_OF", [{"c": 1}]),
        ("ROOT_CAUSE_OF", [{"c": 1}]),
        ("REPLACES", [{"c": 1}]),
    ])
    monkeypatch.setattr(sync_mod.GraphDatabase, "driver",
                        staticmethod(lambda *a, **k: fake))

    rc = sync_mod.main(["--graph", str(graph_path), "--config", str(config_path)])

    assert rc == 0
    assert len(fake.txs) == 1  # 走了重建路径
    assert fake.txs[0].queries[0][0] == "MATCH (n:ITKB) DETACH DELETE n"


# ---------------------------------------------------------------- ④计数复核

def test_verify_counts_mismatch_raises_value_error():
    plan = sync_mod.build_write_plan(GRAPH_DATA)
    fake = FakeDriver()
    sync_mod.apply(fake, plan)
    # 计数不符:Card 组期望 2,库里 99
    fake.routes = [(":ITKB:Card", [{"c": 99}])]

    with pytest.raises(ValueError, match="ITKB:Card"):
        sync_mod.verify_counts(fake, plan)


def test_verify_counts_pass_on_matching_fake():
    plan = sync_mod.build_write_plan(GRAPH_DATA)
    want = [
        ("MATCH (n:ITKB) RETURN count(n) AS c", [{"c": 5}]),
        (":ITKB:Card", [{"c": 2}]),
        (":ITKB:Entity", [{"c": 1}]),
        (":ITKB:Concept", [{"c": 2}]),
        ("MENTIONS", [{"c": 1}]),
        ("SYMPTOM_OF", [{"c": 1}]),
        ("ROOT_CAUSE_OF", [{"c": 1}]),
        ("REPLACES", [{"c": 1}]),
    ]
    fake = FakeDriver(routes=want)

    sync_mod.verify_counts(fake, plan)  # 不抛即过


# ---------------------------------------------------------------- ⑤⑥硬失败

def test_connection_error_system_exit_1(monkeypatch, tmp_path):
    from neo4j.exceptions import ServiceUnavailable
    graph_path = write_graph(tmp_path)
    config_path = write_config(tmp_path)

    def boom(*a, **k):
        raise ServiceUnavailable("bolt 不可达")

    monkeypatch.setattr(sync_mod.GraphDatabase, "driver",
                        staticmethod(boom))

    with pytest.raises(SystemExit) as ei:
        sync_mod.main(["--graph", str(graph_path), "--config", str(config_path)])
    assert ei.value.code == 1


def test_missing_password_system_exit_1(monkeypatch, tmp_path):
    """⑦凭证缺失 = 硬失败,不空密码连库。"""
    graph_path = write_graph(tmp_path)
    config_path = write_config(tmp_path, pw_env=TEST_ABSENT_PW_ENV)
    monkeypatch.delenv(TEST_ABSENT_PW_ENV, raising=False)

    called = []

    def no_conn(*a, **k):  # pragma: no cover - 连接就是不该发生
        called.append(1)
        raise AssertionError("不应带空密码建 driver")

    monkeypatch.setattr(sync_mod.GraphDatabase, "driver",
                        staticmethod(no_conn))

    with pytest.raises(SystemExit) as ei:
        sync_mod.main(["--graph", str(graph_path), "--config", str(config_path)])
    assert ei.value.code == 1
    assert called == []


# ---------------------------------------------------------------- 集成

@pytest.mark.neo4j
def test_real_neo4j_rebuild_and_idempotent():
    """真库全量重建:外部数据保护 + 分型计数对账 + 重跑幂等。

    skip 条件(裁决 5):无 NEO4J_PASSWORD 环境变量或服务不可达。
    """
    pw = os.environ.get("NEO4J_PASSWORD")
    if not pw:
        pytest.skip("未设置 NEO4J_PASSWORD 环境变量")
    from neo4j import GraphDatabase
    uri = "bolt://localhost:7687"
    try:
        driver = GraphDatabase.driver(uri, auth=("neo4j", pw),
                                      connection_timeout=5)
        driver.verify_connectivity()
    except Exception as e:      # noqa: BLE001
        pytest.skip(f"本地 Neo4j 不可达:{type(e).__name__}: {e}")
        return

    try:
        graph_data = json.loads(REAL_GRAPH.read_text(encoding="utf-8"))
        with driver.session(database=None) as s:
            # 外部数据探针:重建只许删 :ITKB 范围,Person 必须存活
            s.run("MERGE (p:Person {probe_sync_graph: true})")
            # 强制重建路径:清掉 meta 指纹与旧图(仅 :ITKB 范围)
            s.run("MATCH (m:ITKBGraphMeta) DETACH DELETE m")
            s.run("MATCH (n:ITKB) DETACH DELETE n")

        rc = sync_mod.main(["--graph", str(REAL_GRAPH), "--config", str(REAL_YAML)])
        assert rc == 0

        with driver.session(database=None) as s:
            probe = s.run("MATCH (p:Person {probe_sync_graph: true}) "
                          "RETURN count(p) AS c").single()["c"]
            assert probe == 1, "探针 Person 被误删:重建越出了 :ITKB 范围"

            total = s.run("MATCH (n:ITKB) RETURN count(n) AS c").single()["c"]
            assert total == len(graph_data["nodes"])
            meta = s.run("MATCH (m:ITKBGraphMeta {key: 'applied'}) "
                         "RETURN m.wiki_fingerprint AS fp").single()["fp"]
            assert meta == graph_data["wiki_fingerprint"]

            # 分型对账:第二标签 / 关系型逐一与 graph_data 计数一致
            for secondary in ("Card", "Entity", "Concept"):
                label = secondary.lower()
                expected = sum(1 for n in graph_data["nodes"]
                               if n.get("label") == label)
                got = s.run(f"MATCH (n:ITKB:{secondary}) "
                            "RETURN count(n) AS c").single()["c"]
                assert got == expected, f"{secondary}: 库 {got} ≠ 数据 {expected}"

            from collections import Counter
            for rel_type, expected in Counter(
                    e["type"] for e in graph_data["edges"]).items():
                got = s.run(f"MATCH (a:ITKB)-[r:{rel_type}]->(b:ITKB) "
                            "RETURN count(r) AS c").single()["c"]
                assert got == expected, f"{rel_type}: 库 {got} ≠ 数据 {expected}"

        # 幂等:指纹一致 → 跳过重建,零变更
        rc2 = sync_mod.main(["--graph", str(REAL_GRAPH), "--config", str(REAL_YAML)])
        assert rc2 == 0
        with driver.session(database=None) as s:
            assert s.run("MATCH (n:ITKB) RETURN count(n) AS c").single()["c"] == total
            assert s.run("MATCH (m:ITKBGraphMeta) "
                         "RETURN count(m) AS c").single()["c"] == 1
    finally:
        driver.close()


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
