# -*- coding: utf-8 -*-
"""GraphExpander(一跳扩展)与装配/HTTP 接线测试(Task 10)。

分三层:
- **扩展器纯逻辑**:伪造 driver(会话返回固定行),验证白名单外边型不产出、
  单源 max_neighbors 截断、已在 base 的邻居去重、衰减分与扩展键、非现行邻居
  不入、parents_by_id 缺邻居跳过并计数、批查询参数(ids/whitelist/cap/Cypher 文本)、
  ServiceUnavailable/超时/建连失败 → GraphUnavailable(保留真实原因);
- **装配接线**:bare ServiceAssembly + 真 GraphExpander(伪 driver),验证
  search() 在 _run_search 之后、build_response 之前把扩展条目追加到
  final_results 尾部;rejected / 空 final_results 短路不触库;
  GraphUnavailable 穿透且检索锁释放;
- **HTTP 与生命周期**:create_app 注入装配件,验证金标④(graph.enabled=false
  默认下响应与改造前逐字段一致 + expand 零调用)、GraphUnavailable → 503/5032、
  lifespan 退出时关闭 Neo4j driver。

真库冒烟标 @pytest.mark.neo4j(密码可从环境变量 NEO4J_PASSWORD 或
services/python-retrieval/.env 解析时才执行):只验证接线与条目不变量,
不依赖具体图的边数据。
"""

import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from neo4j.exceptions import ServiceUnavailable  # noqa: E402

import rag_service.assembly as assembly_mod  # noqa: E402
import rag_service.graph_expansion as expansion_mod  # noqa: E402
from rag_pipeline.config import (  # noqa: E402
    ExpansionConfig, GraphConfig, Neo4jConfig, load_config)
from rag_service.app import create_app  # noqa: E402
from rag_service.assembly import ServiceAssembly, _parents_index_from_corpus  # noqa: E402
from rag_service.contract import RetrievalRequest  # noqa: E402
from rag_service.graph_expansion import (  # noqa: E402
    GRAPH_UNAVAILABLE_MSG, GraphExpander, GraphUnavailable)

if __name__ == "__main__":
    pytest.main([__file__, "-q"])


# ---------------------------------------------------------------- 造数据

def graph_cfg(**expansion_over) -> GraphConfig:
    e = ExpansionConfig()
    for k, v in expansion_over.items():
        setattr(e, k, v)
    return GraphConfig(enabled=True, neo4j=Neo4jConfig(password="local-test"), expansion=e)


def base_item(pid: str, score: float) -> Dict[str, Any]:
    """hybrid_rerank_search final_results 条目的最小形态(键见 hybrid.py:339-347)。"""
    return {
        "content": f"{pid} 子块正文",
        "metadata": {
            "parent_id": pid,
            "child_id": f"{pid}#c0",
            "chunk_id": f"{pid}#c0",
            "Header_1": f"{pid}卡的标题",
            "parent_content": f"{pid} 卡全文正文",
            "wiki_status": "现行",
            "wiki_version": "v1.0",
        },
        "rerank_score": score,
    }


def parent_md(pid: str, *, status: str = "现行",
              title: Optional[str] = None) -> Dict[str, Any]:
    """parents_by_id 的值形态:父块代表 metadata(build_response 读得到的位置)。"""
    return {
        "parent_id": pid,
        "Header_1": title or f"{pid}卡的标题",
        "parent_content": f"{pid} 卡全文正文",
        "wiki_status": status,
        "wiki_version": "v1.0",
    }


def row(src: str, nid: str, rel: str) -> Dict[str, Any]:
    """单批 UNWIND 查询返回的一行(键名与 Cypher RETURN 表达式逐字一致)。"""
    return {"id": src, "n.wiki_id": nid, "type(r)": rel}


class FakeSession:
    """伪 Bolt 会话:run 返回固定行(或由 on_run 动态抛错/出参),并记录查询。"""

    def __init__(self, records: List[Dict[str, Any]],
                 on_run: Any = None):
        self._records = records
        self._on_run = on_run
        self.runs: List[Any] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **params):
        self.runs.append((query, params))
        if self._on_run is not None:
            return self._on_run(query, params)
        return list(self._records)

    def __iter__(self):
        # __enter__ 路径之外不支持迭代(Match 用不到)
        raise AssertionError("应经 session.run 的返回值消费结果")


class FakeDriver:
    """伪 Neo4j driver:懒构造/复用/关闭语义对齐真 driver 测试所需的最小面。"""

    def __init__(self, records: Optional[List[Dict[str, Any]]] = None,
                 on_run: Any = None):
        self.records = records or []
        self.on_run = on_run
        self.sessions: List[FakeSession] = []
        self.closed = False

    def session(self, **kw):
        s = FakeSession(self.records, self.on_run)
        self.sessions.append(s)
        return s

    def close(self):
        self.closed = True


def expander_with(driver: FakeDriver, cfg: Optional[GraphConfig] = None) -> GraphExpander:
    exp = GraphExpander(cfg or graph_cfg())
    exp._driver = driver          # 进程级懒初始化的注入点:_driver 已在则不再建连
    return exp


class FakeRetriever:
    """_run_search 的替身:hybrid_rerank_search 返回固定结果字典。"""

    def __init__(self, results: List[Dict[str, Any]], *, rejected: bool = False):
        self._results = results
        self._rejected = rejected
        self.calls: List[Dict[str, Any]] = []

    def hybrid_rerank_search(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "final_results": list(self._results),
            "rejected": self._rejected,
            "rerank_remote": True,
            "max_rerank_score": max((r["rerank_score"] for r in self._results), default=0.0),
        }


def _bare_assembly(results: List[Dict[str, Any]], *,
                   rejected: bool = False,
                   graph_expander: Any = None,
                   parents_by_id: Optional[Dict[str, Dict[str, Any]]] = None) -> ServiceAssembly:
    """绕过 __init__(不加载向量库):search() 方法体所需的最小属性集。"""
    asm = ServiceAssembly.__new__(ServiceAssembly)
    asm.cfg = load_config()
    asm.retriever = FakeRetriever(results, rejected=rejected)
    asm.rewriter = None
    asm.serialize_search = True
    asm.lock_wait_seconds = 5.0
    asm._lock = threading.Lock()
    asm.mapping = {"ITKB-ACC-001": {"articleId": "9001", "versionId": "v5", "categoryId": "C_ACC"}}
    asm.rerank_degraded_count = 0
    # graph.enabled=false 时 __init__ 留下的正是 None——与真实装配状态一致
    asm.graph_expander = graph_expander
    asm._parents_by_id = parents_by_id or {}
    return asm


def _client_for(asm) -> "TestClient":
    return TestClient(create_app(assembly=asm), raise_server_exceptions=False)


# ---------------------------------------------------------------- ① 白名单

def test_whitelist_excludes_replaces_and_mentions():
    """金标③(python 半边):白名单外的边型(REPLACES/MENTIONS)绝不产出条目。

    Cypher 服务端过滤 type(r) IN $whitelist;python 侧对返回行再做一次白名单
    复核,防线独立于查询文本。
    """
    driver = FakeDriver([row("S", "N1", "SAME_ROOT_CAUSE"),
                         row("S", "N2", "REPLACES"),
                         row("S", "N3", "MENTIONS")])
    exp = expander_with(driver)
    entries = exp.expand([base_item("S", 0.9)], {"N1": parent_md("N1"),
                                                  "N2": parent_md("N2"),
                                                  "N3": parent_md("N3")})
    assert [e["metadata"]["parent_id"] for e in entries] == ["N1"]


# ---------------------------------------------------------------- ② 截断

def test_max_neighbors_caps_per_source():
    """单源扩展数量上限:服务端 LIMIT 是总量兜底,python 侧按源精确截断。"""
    driver = FakeDriver([row("S", "N1", "RELATED"),
                         row("S", "N2", "RELATED"),
                         row("S", "N3", "RELATED")])  # 已按 n.wiki_id 排序
    exp = expander_with(driver, graph_cfg(max_neighbors=2))
    entries = exp.expand([base_item("S", 0.8)],
                          {f"N{i}": parent_md(f"N{i}") for i in (1, 2, 3)})
    assert [e["metadata"]["parent_id"] for e in entries] == ["N1", "N2"]


def test_max_neighbors_is_per_source():
    """上限按源计数:两个源各自 max_neighbors,不共享配额。"""
    driver = FakeDriver([row("S1", "N1", "RELATED"),
                         row("S1", "N2", "RELATED"),
                         row("S2", "N3", "RELATED"),
                         row("S2", "N4", "RELATED")])
    exp = expander_with(driver, graph_cfg(max_neighbors=2))
    entries = exp.expand([base_item("S1", 0.8), base_item("S2", 0.7)],
                          {f"N{i}": parent_md(f"N{i}") for i in (1, 2, 3, 4)})
    assert [(e["graph_expanded_from"], e["metadata"]["parent_id"]) for e in entries] == \
        [("S1", "N1"), ("S1", "N2"), ("S2", "N3"), ("S2", "N4")]


# ---------------------------------------------------------------- ③ 去重

def test_neighbor_already_in_base_is_skipped():
    """命中卡本身(或其子块)已是 base 邻居 → 不重复产出。"""
    driver = FakeDriver([row("S", "B1", "RELATED"), row("S", "N2", "RELATED")])
    exp = expander_with(driver)
    entries = exp.expand([base_item("S", 0.9), base_item("B1", 0.6)],
                          {"B1": parent_md("B1"), "N2": parent_md("N2")})
    assert [e["metadata"]["parent_id"] for e in entries] == ["N2"]


def test_same_neighbor_two_whitelisted_edges_dedups_once():
    """同源同邻居多条白名单边:只产出首条(查询已按 n.wiki_id 排序,首条确定)。"""
    driver = FakeDriver([row("S", "N1", "RELATED"), row("S", "N1", "SAME_ROOT_CAUSE")])
    exp = expander_with(driver)
    entries = exp.expand([base_item("S", 0.8)], {"N1": parent_md("N1")})
    assert len(entries) == 1
    assert entries[0]["graph_relation"] == "RELATED"


def test_sources_deduped_first_score_wins():
    """base 里同卡的多个子块只算一个源(去重);衰减分用首次出现的 rerank_score。"""
    driver = FakeDriver([row("S", "N1", "RELATED")])
    exp = expander_with(driver)
    entries = exp.expand([base_item("S", 0.8), base_item("S", 0.6)],
                          {"N1": parent_md("N1")})
    assert entries[0]["rerank_score"] == round(0.8 * 0.5, 4)
    ids_param = driver.sessions[0].runs[0][1]["ids"]
    assert ids_param == ["S"]


# ---------------------------------------------------------------- ④ 衰减分与扩展键

def test_entry_shape_decay_score_and_internal_keys():
    """条目 = 父块代表 + 衰减分 + 三内部键(graph_expanded/…from/graph_relation);不就地改 base。"""
    driver = FakeDriver([row("S", "N1", "SAME_ROOT_CAUSE")])
    exp = expander_with(driver, graph_cfg(decay=0.5))
    base = [base_item("S", 0.76)]
    base_snapshot = [dict(b) for b in base]
    p = parent_md("N1")
    entries = exp.expand(base, {"N1": p})
    assert len(entries) == 1
    e = entries[0]
    assert e["content"] == p["parent_content"]
    assert e["metadata"] == p
    assert e["rerank_score"] == round(0.76 * 0.5, 4)
    assert e["graph_expanded"] is True
    assert e["graph_expanded_from"] == "S"
    assert e["graph_relation"] == "SAME_ROOT_CAUSE"
    # 基础结果未被就地改动
    assert base == base_snapshot
    assert base[0] is not e


# ---------------------------------------------------------------- ⑤ 现行门

def test_non_current_neighbor_not_expanded():
    """非'现行'邻居(已废止/已下线)绝不入扩展条目;计数留痕。"""
    driver = FakeDriver([row("S", "N1", "RELATED"), row("S", "N2", "RELATED")])
    exp = expander_with(driver)
    entries = exp.expand([base_item("S", 0.8)],
                         {"N1": parent_md("N1", status="现行"),
                          "N2": parent_md("N2", status="已废止")})
    assert [e["metadata"]["parent_id"] for e in entries] == ["N1"]
    assert exp.last_stats["non_current"] == 1

    exp2 = expander_with(FakeDriver([row("S", "N2", "RELATED")]))
    entries2 = exp2.expand([base_item("S", 0.8)], {"N2": parent_md("N2", status="已下线")})
    assert entries2 == []
    assert exp2.last_stats["non_current"] == 1


# ---------------------------------------------------------------- ⑥ 缺父块

def test_missing_parent_metadata_skips_without_crash():
    """parents_by_id 缺该邻居(或父块 metadata 空内容)→ 跳过并计数,不崩。"""
    driver = FakeDriver([row("S", "N1", "RELATED"), row("S", "GHOST", "RELATED")])
    exp = expander_with(driver)
    entries = exp.expand([base_item("S", 0.8)], {"N1": parent_md("N1")})
    assert [e["metadata"]["parent_id"] for e in entries] == ["N1"]
    assert exp.last_stats["missing_parent"] == 1

    # 空正文同罪:内容三键皆空的父块代表没有产出价值,同样跳过
    exp2 = expander_with(FakeDriver([row("S", "EMPTY", "RELATED")]))
    entries2 = exp2.expand([base_item("S", 0.8)], {"EMPTY": {"parent_id": "EMPTY"}})
    assert entries2 == []
    assert exp2.last_stats["missing_parent"] == 1


# ---------------------------------------------------------------- ⑦ 硬失败

def _raising_driver(exc):
    def on_run(query, params):
        raise exc
    return FakeDriver(on_run=on_run)


def test_service_unavailable_raises_graph_unavailable():
    driver = _raising_driver(ServiceUnavailable("connection refused"))
    exp = expander_with(driver)
    with pytest.raises(GraphUnavailable) as ei:
        exp.expand([base_item("S", 0.8)], {"N1": parent_md("N1")})
    assert str(ei.value) == GRAPH_UNAVAILABLE_MSG
    assert isinstance(ei.value.__cause__, ServiceUnavailable)   # 真实原因不丢


def test_query_timeout_raises_graph_unavailable():
    exp = expander_with(_raising_driver(TimeoutError("query took too long")))
    with pytest.raises(GraphUnavailable):
        exp.expand([base_item("S", 0.8)], {"N1": parent_md("N1")})


def test_driver_creation_failure_raises_graph_unavailable(monkeypatch):
    """懒构造建连失败(不可达/凭证错)同样硬失败,不返回空扩展。"""

    class _BrokenGraphDatabase:
        @staticmethod
        def driver(*args, **kwargs):
            raise ServiceUnavailable("no route to host")

    monkeypatch.setattr(expansion_mod, "GraphDatabase", _BrokenGraphDatabase)
    exp = GraphExpander(graph_cfg())
    with pytest.raises(GraphUnavailable):
        exp.expand([base_item("S", 0.8)], {"N1": parent_md("N1")})
    # close 幂等:建连失败后关闭不抛
    exp.close()


def test_expand_zero_sources_never_touches_graph():
    """base 为空 → 无源可扩展,不触碰图库零查询。"""
    driver = FakeDriver([])
    exp = expander_with(driver)
    assert exp.expand([], {"N1": parent_md("N1")}) == []
    assert driver.sessions == []     # 连会话都没开
    assert exp.last_stats["rows"] == 0    # 连图查询都没跑


# ---------------------------------------------------------------- 批查询参数

def test_single_batch_unwind_query_shape():
    """单批 UNWIND:ids 去重有序、whitelist/cap 进参数、Bolt 查询超时按配置。"""
    driver = FakeDriver([row("S1", "N1", "RELATED")])
    exp = expander_with(driver, graph_cfg(max_neighbors=2))
    exp.expand([base_item("S1", 0.8), base_item("S2", 0.5), base_item("S1", 0.4)],
               {"N1": parent_md("N1")})
    query, params = driver.sessions[0].runs[0]
    # 合并超时预算:单批查询带 timeout_ms(Bolt Query 级超时,毫秒折秒)
    assert getattr(query, "timeout", None) == 0.3
    assert "UNWIND $ids AS id" in query.text
    assert "type(r) IN $whitelist" in query.text
    assert "n.status = '现行'" in query.text
    assert "ORDER BY n.wiki_id" in query.text
    assert "LIMIT $cap" in query.text
    assert params["ids"] == ["S1", "S2"]                      # 去重、保序
    assert params["whitelist"] == ["SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES"]
    assert params["cap"] == 2 * 2                             # 源数 × max_neighbors


# ---------------------------------------------------------------- 父块索引

def test_parents_index_from_corpus_strips_child_ids():
    """语料文档 → {parent_id: 父块 metadata}:子块专属 child_id/chunk_id 剥离,
    parent_content/身份字段保留;同父多子块只取首块。"""

    class Doc:
        def __init__(self, text, md):
            self.page_content = text
            self.metadata = md

    d1 = Doc("子块一", {"parent_id": "S", "child_id": "S#c0", "chunk_id": "S#c0",
                       "parent_content": "S 全文", "wiki_status": "现行",
                       "Header_1": "S卡的标题", "child_idx": 0})
    d2 = Doc("子块二", {"parent_id": "S", "child_id": "S#c1", "chunk_id": "S#c1",
                       "parent_content": "S 全文", "wiki_status": "现行",
                       "Header_1": "S卡的标题", "child_idx": 1})
    parents = _parents_index_from_corpus([d1, d2])
    assert list(parents.keys()) == ["S"]
    assert parents["S"] == {"parent_id": "S", "parent_content": "S 全文",
                            "wiki_status": "现行", "Header_1": "S卡的标题",
                            "child_idx": 0}     # 首块为准,children/blocks 来源都可读


# ---------------------------------------------------------------- 装配接线

def test_search_appends_expansion_after_base_results():
    """search():_run_search 之后、build_response 之前,扩展条目追加到基础条目尾部。"""
    driver = FakeDriver([row("ITKB-ACC-001", "ITKB-PRN-002", "RELATED")])
    exp = expander_with(driver, graph_cfg(decay=0.5))
    asm = _bare_assembly([base_item("ITKB-ACC-001", 0.9)],
                         graph_expander=exp,
                         parents_by_id={"ITKB-PRN-002": parent_md("ITKB-PRN-002")})
    resp = asm.search(RetrievalRequest(question="域账号锁定", top_k=5))
    body = resp.model_dump(by_alias=True, exclude_none=True)
    ids = [i["chunkId"] for i in body["items"]]
    # 顺序:基础条目在前,扩展(父块代表)在后——扩展条目 chunkId 回落到 parent_id
    assert ids == ["ITKB-ACC-001#c0", "ITKB-PRN-002"]
    assert body["items"][2 - 1]["score"] == round(0.9 * 0.5, 4)   # 0.45 = 源×decay
    assert body["topScore"] == 0.9                                # topScore 仍取基础条目


def test_rejected_search_skips_expansion():
    """rejected=True 的请求已判拒答 → 不触图库、不加扩展。"""
    driver = FakeDriver([row("ITKB-ACC-001", "ITKB-PRN-002", "RELATED")])
    exp = expander_with(driver)
    asm = _bare_assembly([base_item("ITKB-ACC-001", 0.9)], rejected=True,
                         graph_expander=exp,
                         parents_by_id={"ITKB-PRN-002": parent_md("ITKB-PRN-002")})
    resp = asm.search(RetrievalRequest(question="域账号锁定", top_k=5))
    assert driver.sessions == []            # 一次图查询都没有
    assert resp.model_dump(by_alias=True)["suggestedReplyType"] == "REFUSE"


def test_empty_final_results_skips_expansion():
    """final_results 为空(极端空结果)→ 不触图库。"""
    driver = FakeDriver([])
    exp = expander_with(driver)
    asm = _bare_assembly([], graph_expander=exp, parents_by_id={})
    asm.search(RetrievalRequest(question="域账号锁定", top_k=5))
    assert driver.sessions == []


def test_graph_unavailable_propagates_and_lock_released():
    """图库硬失败原样穿透 search();检索锁在 finally 中释放,不残留互斥。"""
    exp = expander_with(_raising_driver(ServiceUnavailable("refused")),
                        graph_cfg())
    asm = _bare_assembly([base_item("ITKB-ACC-001", 0.9)],
                         graph_expander=exp, parents_by_id={"N1": parent_md("N1")})
    with pytest.raises(GraphUnavailable):
        asm.search(RetrievalRequest(question="域账号锁定", top_k=5))
    assert not asm._lock.locked()           # 锁已还
# ---------------------------------------------------------------- HTTP & 生命周期

BASE = [base_item("ITKB-ACC-001", 0.9), base_item("ITKB-PRN-002", 0.55)]


def test_default_disabled_response_field_snapshot():
    """金标④:graph.enabled=false 默认下,响应与改造前逐字段一致(硬编码快照)。"""
    asm = _bare_assembly(BASE)
    assert asm.cfg.graph.enabled is False          # 真实 pipeline.yaml 默认
    assert asm.graph_expander is None              # 关图即无装配件
    with _client_for(asm) as client:
        resp = client.post("/api/v1/rag/retrievals",
                           json={"question": "域账号锁定", "topK": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == {
        "items": [
            {
                "chunkId": "ITKB-ACC-001#c0",
                "articleId": "9001",
                "versionId": "v5",
                "indexVersion": "v5",
                "title": "ITKB-ACC-001卡的标题",
                "snippet": "ITKB-ACC-001 卡全文正文",
                "content": "ITKB-ACC-001 卡全文正文",
                "categoryId": "C_ACC",
                "score": 0.9,
            },
            {
                "chunkId": "ITKB-PRN-002#c0",
                "articleId": "ITKB-PRN-002",
                "versionId": "v1.0",
                "indexVersion": "v1.0",
                "title": "ITKB-PRN-002卡的标题",
                "snippet": "ITKB-PRN-002 卡全文正文",
                "content": "ITKB-PRN-002 卡全文正文",
                "score": 0.55,
            },
        ],
        "domain": "OFFICE_IT",
        "suggestedReplyType": "ANSWER",
        "topScore": 0.9,
        "reliable": True,
        "publishedOnly": True,
    }


def test_default_disabled_never_touches_expander(monkeypatch):
    """金标④(零调用):关图状态下检索全链路不构造、不调用 GraphExpander。"""
    touched = []

    class _GuardExpander:
        def __init__(self, *a, **k):
            touched.append("init")

        def expand(self, *a, **k):
            touched.append("expand")
            raise AssertionError("graph disabled 却调用了 expand")

    monkeypatch.setattr(assembly_mod, "GraphExpander", _GuardExpander)
    asm = _bare_assembly(BASE)          # graph_expander=None:与 __init__ 关图行为一致
    asm.search(RetrievalRequest(question="域账号锁定", top_k=5))
    assert touched == []


def test_graph_unavailable_maps_to_503_5032():
    """协议映射:GraphUnavailable → HTTP 503,code 5032,消息逐字。"""
    exp = expander_with(_raising_driver(ServiceUnavailable("refused")))
    asm = _bare_assembly(BASE, graph_expander=exp, parents_by_id={"N1": parent_md("N1")})
    with _client_for(asm) as client:
        resp = client.post("/api/v1/rag/retrievals",
                           json={"question": "域账号锁定", "topK": 5})
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == 5032
    assert body["msg"] == GRAPH_UNAVAILABLE_MSG
    assert "data" not in body          # exclude_none:错误包络无 data 键


def test_lifespan_closes_graph_expander_driver():
    """lifespan 退出时显式关闭扩展器的 Neo4j driver(不留孤儿连接)。"""
    driver = FakeDriver([row("ITKB-ACC-001", "ITKB-PRN-002", "RELATED")])
    exp = expander_with(driver)
    asm = _bare_assembly(BASE, graph_expander=exp,
                         parents_by_id={"ITKB-PRN-002": parent_md("ITKB-PRN-002")})
    with _client_for(asm):
        pass
    assert driver.closed is True


def test_lifespan_close_tolerates_stub_assembly():
    """注入的 StubAssembly 无 graph_expander 属性 → 关闭阶段不炸(getattr 兜底)。"""

    class Stub:
        status = "UP"

        def search(self, request):
            from rag_service.mapping import build_response
            return build_response(
                {"final_results": [], "rejected": False, "max_rerank_score": 0.0},
                wiki_mapping={}, request_category_id=None, reject_threshold=0.4)

    with TestClient(create_app(assembly=Stub()), raise_server_exceptions=False):
        pass


# ---------------------------------------------------------------- 真库冒烟(可选)

_neo4j_pw = load_config().graph.neo4j.password


@pytest.mark.neo4j
@pytest.mark.skipif(not _neo4j_pw, reason="NEO4J_PASSWORD 未设置且 .env 不可解析:真库冒烟跳过")
def test_real_graph_smoke():
    """真库冒烟(可选验证):真 driver/真图跑一遍 expand,断言条目不变量。

    不断言具体邻居数(边数据随同步内容与状态过滤变化),只钉死接线与条目形态:
    每条扩展条目必须在白名单关系内、metadata 取自父块索引、分数=源×decay。
    """
    from rag_pipeline.chunking.corpus import load_corpus_with_deterministic_ids
    from rag_pipeline.config import REPO_ROOT

    cfg = load_config()
    exp = GraphExpander(cfg.graph)
    try:
        corpus = load_corpus_with_deterministic_ids(
            REPO_ROOT / "artifacts/output/wiki", cfg)
        parents = _parents_index_from_corpus(corpus)
        entries = exp.expand([base_item("ITKB-ACC-001", 0.9)], parents)
        assert len(entries) <= cfg.graph.expansion.max_neighbors * 1
        for e in entries:
            assert e["graph_expanded"] is True
            assert e["graph_expanded_from"] == "ITKB-ACC-001"
            assert e["graph_relation"] in cfg.graph.expansion.edge_whitelist
            assert e["rerank_score"] == round(0.9 * cfg.graph.expansion.decay, 4)
            assert parents[e["metadata"]["parent_id"]] == e["metadata"]
    finally:
        exp.close()
