# -*- coding: utf-8 -*-
"""版本消歧（rag_pipeline.policy）的守护测试。

覆盖三件容易错的事：
1. **必须看得见废止卡**：`default_exclude` 会在召回前置屏蔽「已废止」卡，
   但要判断「某时刻哪一版有效」，恰恰需要看见旧版 —— resolver 必须以
   `include_excluded=True` 调检索，否则旧规永远选不出来；
2. **沿命中主题的版本链选**，而不是在所有候选里挑日期最大的 —— 一次检索会捎回
   若干不相关卡片，全局取 max 会让同日期的两条链按遍历顺序任选其一（不稳定）；
3. **四种结论不互相冒充**：RESOLVED / NO_EFFECTIVE_VERSION / UNDATED / NO_MATCH。
   尤其 UNDATED —— 没有生效日期的卡不能默认它「永远有效」。

全部为纯逻辑单测（假检索器，不触网、不加载向量库）。
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.policy import (  # noqa: E402
    NO_EFFECTIVE_VERSION, NO_MATCH, RESOLVED, UNDATED,
    PolicyResolver, _as_str_list)

WIKI_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "output" / "wiki"


# ---------------------------------------------------------------- 测试替身

def chunk(article_id: str, *, title: str = "", version: str = "v1.0",
          status: str = "现行", effective: Optional[str] = None,
          replaces: Optional[List[str]] = None, score: float = 0.5,
          content: str = "正文") -> Dict[str, Any]:
    """造一条 hybrid_rerank_search 的 final_results 元素。"""
    md: Dict[str, Any] = {
        "parent_id": article_id,
        "wiki_title": title or f"{article_id} 标题",
        "wiki_version": version,
        "wiki_status": status,
        "parent_content": content,
    }
    if effective is not None:
        md["wiki_effective_date"] = effective
    if replaces is not None:
        md["wiki_replaces"] = json.dumps(replaces, ensure_ascii=False)
    return {"metadata": md, "rerank_score": score, "content": content}


class FakeRetriever:
    """记录调用参数，返回预置结果。"""

    def __init__(self, results: List[Dict[str, Any]]):
        self._results = results
        self.calls: List[Dict[str, Any]] = []

    def hybrid_rerank_search(self, **kwargs):
        self.calls.append(kwargs)
        return {"final_results": list(self._results)}


def build(results: List[Dict[str, Any]]):
    retriever = FakeRetriever(results)
    return PolicyResolver(retriever, corpus_docs=[]), retriever


# 一条干净的两版链：旧版 2022-01-01 起，新版 2024-03-01 起并取代旧版
ACC_CHAIN = [
    chunk("ITKB-ACC-001", title="域账号锁定排查与解锁处理", version="v1.0",
          effective="2024-03-01", replaces=["ITKB-LEG-ACC-001"], score=0.91),
    chunk("ITKB-LEG-ACC-001", title="域账号锁定处理（旧版，已废止）", version="v0.9",
          status="已废止", effective="2022-01-01", score=0.55),
]


# ---------------------------------------------------------------- 分水岭

def test_resolves_old_version_before_cutover():
    resolver, _ = build(ACC_CHAIN)
    res = resolver.resolve("域账号锁定", at="2024-01-15")
    assert res.status == RESOLVED
    assert res.article_id == "ITKB-LEG-ACC-001"
    assert res.version == "v0.9"
    assert res.effective_date == "2022-01-01"
    assert res.superseded_at == "2024-03-01"


def test_resolves_new_version_after_cutover():
    resolver, _ = build(ACC_CHAIN)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert res.status == RESOLVED
    assert res.article_id == "ITKB-ACC-001"
    assert res.version == "v1.0"
    assert res.replaced_articles == ("ITKB-LEG-ACC-001",)
    assert res.superseded_at is None


def test_resolves_new_version_exactly_on_cutover_date():
    """生效日当天即适用新版——边界必须是「>=」而不是「>」。"""
    resolver, _ = build(ACC_CHAIN)
    res = resolver.resolve("域账号锁定", at="2024-03-01")
    assert res.status == RESOLVED
    assert res.article_id == "ITKB-ACC-001"


def test_citation_carries_article_version_and_title():
    resolver, _ = build(ACC_CHAIN)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert res.citation == "[来源: ITKB-ACC-001@v1.0 《域账号锁定排查与解锁处理》]"


def test_replaced_articles_come_from_frontmatter():
    resolver, _ = build(ACC_CHAIN)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert list(res.replaced_articles) == ["ITKB-LEG-ACC-001"]


# ---------------------------------------------------------------- 必须看得见废止卡

def test_search_must_include_excluded_cards():
    """这是整个能力的成立前提：屏蔽了废止卡就无从消歧。"""
    resolver, retriever = build(ACC_CHAIN)
    resolver.resolve("域账号锁定", at="2024-01-15")
    assert retriever.calls, "必须调用过检索"
    assert retriever.calls[0]["include_excluded"] is True


def test_search_disables_reject_threshold():
    """消歧要自己判时间，不能因为打分低就在召回阶段被拒答掐掉候选。"""
    resolver, retriever = build(ACC_CHAIN)
    resolver.resolve("域账号锁定", at="2024-01-15")
    call = retriever.calls[0]
    assert call["reject_threshold"] is None
    assert call["heuristic_reject_threshold"] is None


def test_top_k_is_forwarded():
    resolver, retriever = build(ACC_CHAIN)
    resolver.resolve("域账号锁定", at="2024-01-15", top_k=5)
    assert retriever.calls[0]["final_top_k"] == 5


# ---------------------------------------------------------------- 链式选择

def test_chain_is_chosen_by_relevance_not_by_global_max_date():
    """两条同日期、同版本号的链同时在候选里时，必须按相关度定主题。

    这两条链日期一样（2024-03-01）、版本号一样（v1.0）。若实现是「在全部候选里挑
    日期最大的」，取谁取决于遍历顺序 —— 换个顺序答案就变了。
    """
    results = [
        chunk("ITKB-NET-004", title="DNS 解析失败", version="v1.0",
              effective="2024-03-01", replaces=["ITKB-LEG-NET-004"], score=0.42),
        chunk("ITKB-ACC-001", title="域账号锁定", version="v1.0",
              effective="2024-03-01", replaces=["ITKB-LEG-ACC-001"], score=0.93),
        chunk("ITKB-LEG-ACC-001", version="v0.9", status="已废止",
              effective="2022-01-01", score=0.51),
        chunk("ITKB-LEG-NET-004", version="v0.9", status="已废止",
              effective="2022-01-01", score=0.38),
    ]

    forward, _ = build(results)
    backward, _ = build(list(reversed(results)))

    assert forward.resolve("域账号锁定", at="2024-06-01").article_id == "ITKB-ACC-001"
    assert backward.resolve("域账号锁定", at="2024-06-01").article_id == "ITKB-ACC-001"


def test_chain_only_follows_declared_replaces_edges():
    """没有 replaces 声明的卡不会被软匹配串进链——猜出来的版本关系比没有更危险。"""
    results = ACC_CHAIN + [
        chunk("ITKB-UNRELATED", title="打印机脱机", version="v1.0",
              effective="2023-01-01", score=0.10),
    ]
    resolver, _ = build(results)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert "ITKB-UNRELATED" not in {c.article_id for c in res.chain}
    assert res.article_id == "ITKB-ACC-001"


def test_chain_includes_unretrieved_newer_version_via_replaces():
    """只召回旧版时，靠旧版被谁 replaces 也能把新版拉进链——否则会误判「旧版仍有效」。"""
    results = [
        chunk("ITKB-LEG-ACC-001", version="v0.9", status="已废止",
              effective="2022-01-01", score=0.80),
        chunk("ITKB-ACC-001", version="v1.0", effective="2024-03-01",
              replaces=["ITKB-LEG-ACC-001"], score=0.30),
    ]
    resolver, _ = build(results)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert res.status == RESOLVED
    assert res.article_id == "ITKB-ACC-001"


# ---------------------------------------------------------------- 四种结论

def test_undated_when_chain_has_no_effective_date():
    results = [chunk("ITKB-HW-002", title="打印机脱机", version="v1.0", score=0.8)]
    resolver, _ = build(results)
    res = resolver.resolve("打印机脱机", at="2024-06-01")
    assert res.status == UNDATED
    assert res.article_id is None
    assert res.citation is None
    assert res.undated_articles == ("ITKB-HW-002",)
    assert "不猜" in res.reason


def test_no_effective_version_when_all_versions_start_later():
    results = [
        chunk("ITKB-NEW", version="v1.0", effective="2025-01-01", score=0.8),
    ]
    resolver, _ = build(results)
    res = resolver.resolve("某新规", at="2024-06-01")
    assert res.status == NO_EFFECTIVE_VERSION
    assert res.article_id is None
    assert "2025-01-01" in res.reason


def test_no_match_on_empty_retrieval():
    resolver, _ = build([])
    res = resolver.resolve("查不到的东西", at="2024-06-01")
    assert res.status == NO_MATCH
    assert res.article_id is None
    assert "零命中" in res.reason


def test_undated_cards_do_not_block_a_dated_chain():
    """链内混有没日期的卡时，仍按有日期的卡出结论，并把没日期的那张如实列出。"""
    results = [
        chunk("ITKB-ACC-001", version="v1.0", effective="2024-03-01",
              replaces=["ITKB-LEG-ACC-001"], score=0.91),
        chunk("ITKB-LEG-ACC-001", version="v0.9", status="已废止", score=0.55),  # 无生效日
    ]
    resolver, _ = build(results)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert res.status == RESOLVED
    assert res.article_id == "ITKB-ACC-001"
    assert res.undated_articles == ("ITKB-LEG-ACC-001",)


def test_unrelated_undated_card_stays_out_of_undated_report():
    """链外的不相关卡没有日期，不该混进 undated 报告——那是噪音。"""
    results = ACC_CHAIN + [chunk("ITKB-UNRELATED", version="v1.0", score=0.05)]
    resolver, _ = build(results)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert res.status == RESOLVED
    assert res.undated_articles == ()


# ---------------------------------------------------------------- 归并与解析

def test_multiple_chunks_of_one_card_are_merged_taking_best_score():
    results = [
        chunk("ITKB-ACC-001", version="v1.0", effective="2024-03-01",
              replaces=["ITKB-LEG-ACC-001"], score=0.30, content="子块A"),
        chunk("ITKB-ACC-001", version="v1.0", effective="2024-03-01",
              replaces=["ITKB-LEG-ACC-001"], score=0.88, content="整卡全文"),
    ]
    resolver, _ = build(results)
    res = resolver.resolve("域账号锁定", at="2024-06-01")
    assert len([c for c in res.candidates if c.article_id == "ITKB-ACC-001"]) == 1
    assert res.content == "整卡全文"


def test_replaces_parsed_from_json_string():
    assert _as_str_list('["A", "B"]') == ["A", "B"]
    assert _as_str_list("[]") == []
    assert _as_str_list(None) == []
    assert _as_str_list("不是 JSON") == []
    assert _as_str_list('{"not": "a list"}') == []


def test_none_at_defaults_to_today():
    resolver, _ = build(ACC_CHAIN)
    res = resolver.resolve("域账号锁定", at=None)
    # 不关心具体结论，只要不抛异常且状态合法
    assert res.status in (RESOLVED, NO_EFFECTIVE_VERSION, UNDATED, NO_MATCH)


def test_invalid_at_falls_back_to_today_without_crashing():
    resolver, _ = build(ACC_CHAIN)
    res = resolver.resolve("域账号锁定", at="不是日期")
    assert res.status in (RESOLVED, NO_EFFECTIVE_VERSION, UNDATED, NO_MATCH)


# ---------------------------------------------------------------- 真实语料契约

def _read_frontmatter(card_id: str) -> Dict[str, str]:
    text = (WIKI_DIR / f"{card_id}.md").read_text(encoding="utf-8")
    end = text.index("---", 3)
    meta: Dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta


@pytest.mark.skipif(not WIKI_DIR.exists(), reason="本地 wiki 语料不存在")
@pytest.mark.parametrize("new_id,old_id,cutover", [
    ("ITKB-ACC-001", "ITKB-LEG-ACC-001", "2024-03-01"),
    ("ITKB-NET-004", "ITKB-LEG-NET-004", "2024-03-01"),
    ("ITKB-VPN-001", "ITKB-LEG-VPN-001", "2024-03-01"),
])
def test_real_corpus_keeps_the_three_demo_version_chains(new_id, old_id, cutover):
    """语料里那 3 组演示版本链必须完整：新版声明 replaces 旧版、两者都有生效日、
    且新版生效日晚于旧版。少了任何一条，分水岭消歧就演示不出来。

    这 6 张卡的日期是**课程构造数据**（effective_date_source=demo-constructed），
    重跑 wiki_generator 会丢——本用例就是那个提醒。
    """
    new, old = _read_frontmatter(new_id), _read_frontmatter(old_id)

    assert json.loads(new["replaces"]) == [old_id], f"{new_id} 必须声明取代 {old_id}"
    assert new.get("effective_date") == cutover
    assert old.get("effective_date") == "2022-01-01"
    assert new["effective_date_source"] == "demo-constructed"
    assert old["effective_date_source"] == "demo-constructed"
    assert old["status"] == "已废止"
    assert new["effective_date"] > old["effective_date"]