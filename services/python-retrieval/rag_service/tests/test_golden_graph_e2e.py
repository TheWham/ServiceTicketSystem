# -*- coding: utf-8 -*-
"""Task 14 — 四金标链路级端到端验收 + GraphUnavailable 硬失败演练(真 Neo4j + 开图)。

前置 skip 条件(brief Step 1 逐字):`NEO4J_PASSWORD` 未设或 `graph.enabled` 未开
则 skip(保障 CI/未部署图库环境零影响)。运行前临时把 `configs/pipeline.yaml`
段的 `graph.enabled` 翻 `true`(运行后还原,不入库),真库同步见
`tools/sync_graph_to_neo4j.py`。

金标归属:
① 低分扩展条目能到达生成器 — 链路断言:开图请求命中含白名单邻居的卡,
   响应 items 含 graphExpanded=true 条目、其 score < topScore、
   topScore == max(基础条目 score);
② 未过 PUBLISHED 的扩展条目被拦 — Java 侧单测已在 Task 12-② 钉死(
   RetrievalPolicyGraphExpansionTest),本文件按 brief Step 1-②"执行者择一"
   采取「直接引用其结论标注 SKIP 理由」;
③ 沿 REPLACES 的邻居永不到达 — 请求命中含 REPLACES 邻居的卡
   (ITKB-ACC-001 / ITKB-VPN-001 / ITKB-NET-004 各带 REPLACES 邻居),
   断言响应无 relation=REPLACES 条目;
④ graph.enabled=false 行为与改造前完全一致 — 关图(独立装配 instance,
   graph.enabled=false)同一问题集响应与开图响应剥离扩展条目后逐字段等价
   (content/score/topScore/reliable;items 顺序稳定);关图响应本身无任何
   图字段(三键完全缺席),且其逐字段快照已在 Task 10-⑨
   (test_graph_expansion.py::test_default_disabled_response_field_snapshot)
   与改造前硬编码 fixture 钉死,此处补链路级等价半边。

硬失败演练(brief Step 3):图开状态、改 uri 为不可达(brief 允许
"停掉 Neo4j 或改 uri 为不可达"中的后者,不动共享容器)发请求,
断言 HTTP 503 + code 5032 + msg=图库不可用(而非无图结果)。
"""

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import rag_service.assembly as assembly_mod  # noqa: E402
from rag_pipeline.config import load_config  # noqa: E402
from rag_service.app import create_app  # noqa: E402
from rag_service.assembly import ServiceAssembly  # noqa: E402
from rag_service.graph_expansion import (  # noqa: E402
    GRAPH_UNAVAILABLE_MSG, GraphExpander)

if __name__ == "__main__":
    pytest.main([__file__, "-q"])


# ---------------------------------------------------------------- 问题集

def _golden_questions() -> List[Dict[str, Any]]:
    """黄金集取题:①③④共用同一问题集,均命中带 REPLACES 邻居的卡。

    - GOLDEN-QA-014 → ITKB-ACC-001(REPLACES→ITKB-LEG-ACC-001;
      白名单邻居 ITKB-ACC-002/VPN-003/MAIL-003);
    - GOLDEN-QA-013 → ITKB-VPN-001(REPLACES→ITKB-LEG-VPN-001;多 RELATED 邻居);
    - GOLDEN-QA-015 → ITKB-NET-004(REPLACES→ITKB-LEG-NET-004)。
    """
    repo_root = Path(__file__).resolve().parents[2]
    golden = json.loads(
        (repo_root / "evals" / "golden_dataset_v1.0.json").read_text(encoding="utf-8"))
    wanted = {"GOLDEN-QA-014", "GOLDEN-QA-013", "GOLDEN-QA-015"}
    picked = [q for q in golden if q.get("id") in wanted]
    assert {q["id"] for q in picked} == wanted, "黄金集缺题:配置漂移"
    return picked


QUESTIONS = _golden_questions()

WHITELIST = ("SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES")


def _retrieve(client: TestClient, question: str, top_k: int = 5) -> Dict[str, Any]:
    """发一次检索请求,返回 data(断言 200/code==0)。"""
    resp = client.post("/api/v1/rag/retrievals",
                       json={"question": question, "topK": top_k})
    assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
    envelope = resp.json()
    assert envelope.get("code") == 0, f"envelope: {envelope}"
    return envelope["data"]


def _items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return data.get("items") or []


# ---------------------------------------------------------------- 前置与装配

def _skip_if_precondition_unmet() -> None:
    """brief Step 1 逐字:NEO4J_PASSWORD 未设或 graph.enabled 未开则 skip。"""
    cfg = load_config()
    # 凭证解析口径与 rag_pipeline.config 一致:进程环境 > REPO_ROOT/.env;
    # load_config 已把解析结果填进 g.neo4j.password(未设即空串)。
    if not (os.environ.get(cfg.graph.neo4j.password_env)
            or cfg.graph.neo4j.password):
        pytest.skip("NEO4J_PASSWORD 未设:graph_e2e 需真库+开图,CI/未部署图库零影响")
    if not cfg.graph.enabled:
        pytest.skip("graph.enabled 未开:graph_e2e 需真库+开图"
                    "(临时置 configs/pipeline.yaml graph.enabled=true 后重跑,运行后还原)")


@pytest.fixture(scope="module")
def graph_on_asm() -> ServiceAssembly:
    """开图真装配(真语料/真向量库/真图库 driver)。"""
    _skip_if_precondition_unmet()
    asm = ServiceAssembly()
    assert asm.graph_expander is not None, "graph.enabled=true 应构建 GraphExpander 接线"
    yield asm
    if asm.graph_expander is not None:
        asm.graph_expander.close()


@pytest.fixture(scope="module")
def graph_on_client(graph_on_asm) -> TestClient:
    with TestClient(create_app(graph_on_asm)) as client:
        yield client


@pytest.fixture(scope="module")
def graph_off_client(request) -> TestClient:
    """金标④:同一环境下独立装配一个 graph.enabled=false 服务实例。

    MonkeyPatch.load_config 返回关图配置(copy 后仅翻 enabled),
    生产装配代码零改动——RAG_* 环境注入之外的配置真源只有 pipeline.yaml。
    """
    _skip_if_precondition_unmet()
    cfg = load_config()
    off_cfg = copy.deepcopy(cfg)
    off_cfg.graph.enabled = False
    mp = pytest.MonkeyPatch()
    mp.setattr(assembly_mod, "load_config", lambda: off_cfg)
    try:
        asm = ServiceAssembly()
        assert asm.graph_expander is None, "graph.enabled=false 不建即不接线"
        with TestClient(create_app(asm)) as client:
            yield client
    finally:
        mp.undo()


# ---------------------------------------------------------------- 金标①

@pytest.mark.graph_e2e
def test_golden_1_low_score_expanded_entries_reach_responses(graph_on_client):
    """金标①:开图响应 items 含 graphExpanded=true 条目;其 score<topScore;
    topScore==max(基础条目 score);扩展条目的 expandedFrom 指向基础条目。"""
    hits = 0
    for q in QUESTIONS:
        data = _retrieve(graph_on_client, q["query"])
        base = [it for it in _items(data) if not it.get("graphExpanded")]
        expanded = [it for it in _items(data) if it.get("graphExpanded")]
        if expanded:
            hits += 1
            base_scores = [it["score"] for it in base]
            assert base_scores, "存在扩展条目则必存在基础条目(扩展发生在基础条目之后)"
            assert data["topScore"] == pytest.approx(max(base_scores)), \
                f"topScore 应==max(基础 score),实际 topScore={data['topScore']}"
            for it in expanded:
                assert it["score"] < data["topScore"], \
                    f"扩展条目启发式衰减分必须严格低于源卡/topScore:{it['score']} vs {data['topScore']}"
                assert it["relation"] in WHITELIST
                assert it["expandedFrom"], "扩展条目必须携带 expandedFrom"
        if base:
            # 无扩展命中时也须保持:topScore 只在基础条目中计算
            assert data["topScore"] == pytest.approx(max(it["score"] for it in base))
    assert hits > 0, \
        "全问题集零扩展条目:金标①(低分扩展条目能到达生成器)在本环境不成立"


# ---------------------------------------------------------------- 金标②

@pytest.mark.graph_e2e
def test_golden_2_stale_expanded_neighbor_blocked_link_status():
    """金标②:未过 PUBLISHED 的扩展条目被拦(链路半边)。

    按 brief Step 1-②「执行者择一」,此处采取「直接引用其结论标注 SKIP 理由」:
    拦截谓词的拒绝语义已在 Java 侧单测钉死——
    it-ticket-cloud/consultation-service .../RetrievalPolicyGraphExpansionTest
    ::expandedNeighborFailingPublishedCheckIsDroppedWithoutRefusingWholeAnswer:
    邻居 not-current → material 不含该邻居且不升级为 StaleKnowledge 拒答,
    基础条目仍在(Task 12 commit 4636663,283 绿)。python→Java 链路上第二层
    (8302 的 filterPublishedCurrentHits)同样先拦(见 task-12-report 第④-1 条),
    故链路上不存在「stale 邻居到达生成器」的通路;金标语义由该单测结论承载。
    """
    pytest.skip("金标②由 Java 侧 RetrievalPolicyGraphExpansionTest 钉死"
                "(Task 12-②,material 不含 stale 邻居且不拒整单,基础条目仍在;"
                "8302 filterPublishedCurrentHits 为链路第二层同语义拦截,"
                "见本用例 docstring 与 task-12-report)")


# ---------------------------------------------------------------- 金标③

@pytest.mark.graph_e2e
def test_golden_3_replaces_neighbors_never_reach_responses(graph_on_client):
    """金标③:请求命中含 REPLACES 邻居的卡,响应无 relation=REPLACES 条目。

    问题集命中 ITKB-ACC-001 / ITKB-VPN-001 / ITKB-NET-004,三卡均带
    REPLACES→ITKB-LEG-* 边;任何响应(items 全体)不得出现 relation=REPLACES,
    也不得出现已废止 LEG 卡内容(列为 default_exclude 的 base 半边由
    图查询白名单+非现行过滤在扩展侧复核)。
    """
    for q in QUESTIONS:
        data = _retrieve(graph_on_client, q["query"])
        for it in _items(data):
            assert it.get("relation") != "REPLACES", \
                f"REPLACES 邻居泄漏到响应:{it.get('articleId') or it.get('title')}"
            if it.get("graphExpanded"):
                assert it["relation"] in WHITELIST, \
                    f"扩展条目关系必须在白名单内,得到 {it['relation']}"
                assert "ITKB-LEG" not in (it.get("articleId") or ""), \
                    f"已废止 LEG 卡以扩展条目入场:{it.get('articleId')}"


# ---------------------------------------------------------------- 金标④

@pytest.mark.graph_e2e
def test_golden_4_disabled_response_equivalent_to_off_baseline(
        graph_on_client, graph_off_client):
    """金标④:关图重启同一问题集,响应与开图响应剥离扩展条目后逐字段等价。

    等价口径:content/score/topScore/reliable 等 data 全字段(items 顺序
    稳定——列表即顺序);关图响应不得携带任何图字段(graphExpanded/
    expandedFrom/relation 三键完全缺席)。与改造前的逐字段快照对照由
    Task 10-⑨ test_default_disabled_response_field_snapshot 承载(改造前后
    单一行为真源:graph_off 路径与改造前代码路径逐行相同)。
    """
    for q in QUESTIONS:
        off_data = _retrieve(graph_off_client, q["query"])
        any_graph_keys = [k for it in _items(off_data)
                          for k in ("graphExpanded", "expandedFrom", "relation")
                          if k in it]
        assert not any_graph_keys, f"关图响应携带图字段:{any_graph_keys}"
        if _items(off_data):
            assert off_data["topScore"] == pytest.approx(
                max(it["score"] for it in _items(off_data)))

        on_data = _retrieve(graph_on_client, q["query"])
        stripped = copy.deepcopy(on_data)
        stripped["items"] = [it for it in _items(on_data) if not it.get("graphExpanded")]
        assert off_data == stripped, (
            "关图响应与开图响应的基础部分逐字段不等价:"
            f"\noff={json.dumps(off_data, ensure_ascii=False)[:600]}"
            f"\non(stripped)={json.dumps(stripped, ensure_ascii=False)[:600]}")


# ---------------------------------------------------------------- 硬失败演练(Step 3)

@pytest.mark.graph_e2e
def test_hard_failure_graph_unavailable_503_5032(graph_on_client, graph_on_asm):
    """brief Step 3:图开状态、uri 改不可达(不停共享容器)→ 503/5032/图库不可用。

    断言的是硬失败而非静默回退:不得返回无图结果的 200(拒答包络),也不得
    5031(锁忙)。演练用装配件在 finally 中恢复原 expander,不影响后续用例。
    """
    cfg = load_config()
    bad_cfg = copy.deepcopy(cfg)
    bad_cfg.graph.neo4j.uri = "bolt://127.0.0.1:9"   # 不可达端口
    bad_expander = GraphExpander(bad_cfg.graph)
    orig_expander = graph_on_asm.graph_expander
    graph_on_asm.graph_expander = bad_expander
    try:
        question = QUESTIONS[0]["query"]
        resp = graph_on_client.post("/api/v1/rag/retrievals",
                                    json={"question": question, "topK": 5})
        assert resp.status_code == 503, f"图库不可用应 HTTP 503,得到 {resp.status_code}: {resp.text[:200]}"
        envelope = resp.json()
        assert envelope.get("code") == 5032, f"错误码应为 5032,得到 {envelope}"
        assert envelope.get("msg") == GRAPH_UNAVAILABLE_MSG, \
            f"msg 应为单一事实串「{GRAPH_UNAVAILABLE_MSG}」,得到 {envelope.get('msg')!r}"
        assert "data" not in envelope, "错误包络不含 data(exclude_none)"
    finally:
        bad_expander.close()
        graph_on_asm.graph_expander = orig_expander
