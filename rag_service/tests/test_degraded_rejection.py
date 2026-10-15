# -*- coding: utf-8 -*-
"""rerank 降级时的内核拒答守护测试。

背景（用户实测 + 本次复现）：`hybrid_rerank_search` 的拒答门是
    rejected = reject_threshold is not None and self.reranker.last_used_remote and max_rerank < reject_threshold
`and last_used_remote` 使它在网关 429 / 端点不可用、打分降级为本地启发式时**整体失效**：
启发式虽然算出无关问题最高分只有 ~0.13（远低于 0.40），却因降级而不触发拒答，
内核照常返回候选卡 —— 直接消费内核的路径（离线脚本、未来服务层）会把无关问题当命中。

修复：远程与降级各用一条阈值——远程用 reject_threshold（本端点标定 0.40），
降级用 heuristic_reject_threshold（启发式分档标定 0.25，可配置，None=关闭）。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import rag_pipeline.retrieval.hybrid as hybrid_mod  # noqa: E402
from rag_pipeline.chunking.structure_aware import Document  # noqa: E402
from rag_pipeline.config import load_config  # noqa: E402


class _StubReranker:
    """替身：不触网，分数与降级标志由用例注入。"""

    def __init__(self, scores, remote):
        self._scores = scores
        self.last_used_remote = remote

    def predict(self, pairs):
        return list(self._scores)[:len(pairs)] or [0.0] * len(pairs)


def _make_retriever(monkeypatch):
    """构造只走 BM25 通道的检索器；用替身替换 KspReranker 避免构造期自检触网。

    语料必须互不相同：若三篇文档完全一致，查询词出现在全部文档里 → BM25 的 IDF 为负
    → 被 bm25_search 的「0 分过滤」清空，会误判为"没有候选"。
    """
    monkeypatch.setattr(hybrid_mod, "KspReranker", lambda *a, **k: _StubReranker([0.5], True))
    # 语料必须"分化"：若所有文档都含全部查询词，BM25 的 IDF 为负 → 0 分过滤清空候选，
    # 拿不到候选就验不到拒答门（只有 1 篇含查询词，IDF 才为正）
    texts = [
        "密码过期无法登录 请重置密码并检查密码复杂度要求",
        "打印机脱机无法打印 请检查连接与驱动",
        "VPN 连接后无法访问内网资源 请检查路由与客户端",
        "显示器黑屏无信号 请检查线缆与输入源",
    ]
    docs = [
        Document(page_content=text,
                 metadata={"child_id": f"KB-{i}#c0", "parent_id": f"KB-{i}",
                           "parent_content": "整卡全文" * 200, "wiki_version": "v1.0",
                           "Header_1": f"卡片{i}"})
        for i, text in enumerate(texts)
    ]
    retriever = hybrid_mod.IndustrialHybridRetriever(
        vector_db=None, corpus_docs=docs, reranker_model_name="stub",
        default_exclude={}, reranker_backend="dashscope")
    return retriever


def _search(retriever, **kwargs):
    return retriever.hybrid_rerank_search(
        "密码过期登不进系统怎么办", final_top_k=3, rough_top_k=15,
        reject_threshold=0.40, rerank_granularity="parent", **kwargs)


def test_degraded_low_score_is_rejected_by_kernel(monkeypatch):
    """降级（启发式）低分：内核必须拒答——修复前因 last_used_remote=False 直接放行。"""
    retriever = _make_retriever(monkeypatch)
    retriever.reranker = _StubReranker([0.1333, 0.05, 0.05], remote=False)

    res = _search(retriever, heuristic_reject_threshold=0.25)

    assert res["rerank_remote"] is False
    assert res["rejected"] is True
    assert res["final_results"] == []


def test_degraded_high_score_is_not_rejected(monkeypatch):
    """降级但启发式高分（本语料正样本常见 0.6~0.99）：不得误拒。"""
    retriever = _make_retriever(monkeypatch)
    retriever.reranker = _StubReranker([0.8833, 0.5, 0.5], remote=False)

    res = _search(retriever, heuristic_reject_threshold=0.25)

    assert res["rejected"] is False
    assert len(res["final_results"]) == 1


def test_remote_mode_still_uses_remote_threshold(monkeypatch):
    """远程成功时口径不变：0.30 仍按远端标定的 0.40 拒答（不受启发式阈值影响）。"""
    retriever = _make_retriever(monkeypatch)
    retriever.reranker = _StubReranker([0.30, 0.20, 0.10], remote=True)

    res = _search(retriever, heuristic_reject_threshold=0.10)   # 即便启发式阈值更低

    assert res["rejected"] is True, "远程路径必须仍用 reject_threshold=0.40"
    assert res["final_results"] == []


def test_degraded_threshold_none_keeps_legacy_behavior(monkeypatch):
    """显式关闭降级阈值（None）：保持旧行为，供需要"降级也给候选"的调用方使用。"""
    retriever = _make_retriever(monkeypatch)
    retriever.reranker = _StubReranker([0.1333, 0.05, 0.05], remote=False)

    res = _search(retriever, heuristic_reject_threshold=None)

    assert res["rejected"] is False
    assert len(res["final_results"]) == 1


def test_pipeline_config_exposes_heuristic_threshold():
    """阈值必须在配置中心可调（唯一真源 configs/pipeline.yaml）。"""
    assert load_config().retrieval.heuristic_reject_threshold == 0.25


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
