# -*- coding: utf-8 -*-
"""内核微改的守护测试（在线服务化前置条件）。

1. KspReranker.last_used_remote 必须是线程本地状态：并发请求各自记录本次
   打分是否走了远程，互不污染（hybrid.py 的拒答/门控判定读它）。
2. QueryRewriter 必须接受 timeout/retries 构造参数：在线模式用 1.2s 短超时、
   不重试，避免冷缓存时把 Java 侧 4.2s 预算吃光。
"""

import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.retrieval.query_rewriter import QueryRewriter  # noqa: E402
from rag_pipeline.retrieval.reranker import KspReranker  # noqa: E402


def _make_reranker():
    # 无 key → available=False，predict 走启发式兜底，不触网
    return KspReranker(model_name="test", cfg={
        "provider": "direct", "base_url": "", "api_key": "", "model": "", "note": ""})


def test_last_used_remote_is_thread_local():
    reranker = _make_reranker()
    reranker.last_used_remote = True          # 主线程标记：本次打分走了远程
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()                        # 与主线程同时越过第一道栅栏
        reranker.last_used_remote = False     # 并发线程：降级启发式
        barrier.wait()
        time.sleep(0.05)
        assert reranker.last_used_remote is False

    t = threading.Thread(target=worker)
    t.start()
    barrier.wait()
    barrier.wait()                            # 等 worker 写完 False
    time.sleep(0.05)
    # 主线程的 True 不得被 worker 线程的 False 覆盖
    assert reranker.last_used_remote is True
    t.join()


def test_last_used_remote_defaults_false_per_thread():
    reranker = _make_reranker()
    seen = []

    def worker():
        seen.append(reranker.last_used_remote)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert seen == [False]


def test_query_rewriter_accepts_timeout_and_retries():
    rw = QueryRewriter(model="m", cache_dir=None, timeout=1.2, retries=1)
    assert rw.retries == 1

    calls = {"n": 0}

    class _Completions:
        def create(self, **kwargs):
            calls["n"] += 1
            raise RuntimeError("模拟网络失败")

    class _Chat:
        completions = _Completions()

    class _FakeClient:
        chat = _Chat()

    rw.client = _FakeClient()
    out = rw.rewrite("从未缓存过的查询")
    assert out == "从未缓存过的查询"           # 失败回落原查询
    assert rw.last_ok is False
    assert calls["n"] == 1                    # retries=1：不重试


def test_query_rewriter_offline_defaults_unchanged():
    rw = QueryRewriter(model="m", cache_dir=None)
    assert rw.retries == 2                    # 离线默认两次尝试，行为不变


def test_query_rewriter_bounds_sdk_retries_for_online_budget(monkeypatch):
    """在线预算必须真的被 1.2s 约束住：OpenAI SDK 默认 max_retries=2，
    会让一次改写实际耗时 = 超时 × 3 次 ≈ 5s+（实测 5443ms），把 Java 侧预算吃光。
    服务侧必须显式传 max_retries=0。"""
    captured = {}

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    import sys
    import types as _types
    fake_mod = _types.ModuleType("openai")
    fake_mod.OpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_mod)
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")

    QueryRewriter(model="m", cache_dir=None, timeout=1.2, retries=1, max_retries=0)

    assert captured.get("timeout") == 1.2
    assert captured.get("max_retries") == 0, "在线模式必须关掉 SDK 重试，否则 1.2s 形同虚设"


def test_query_rewriter_sdk_retries_default_preserved(monkeypatch):
    """离线默认不显式设置 max_retries（沿用 SDK 默认），行为不变。"""
    captured = {}

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    import sys
    import types as _types
    fake_mod = _types.ModuleType("openai")
    fake_mod.OpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_mod)
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")

    QueryRewriter(model="m", cache_dir=None)

    assert captured.get("timeout") == 30.0
    assert "max_retries" not in captured


def test_rerank_post_timeout_is_bounded_by_instance_attr(monkeypatch):
    """单次 /rerank 请求的超时必须可在线收紧：原先硬编码 120s，
    上游一次挂起就能把串行锁占住两分钟（Java 侧 4.2s 早已超时）。"""
    from rag_pipeline.retrieval import reranker as rmod

    reranker = _make_reranker()
    reranker.endpoint = "http://127.0.0.1:1/rerank"
    reranker.REQUEST_TIMEOUT_SECONDS = 2.5
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["timeout"] = timeout
        raise RuntimeError("stop before network")

    monkeypatch.setattr(rmod.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError):
        reranker._post({"model": "m", "query": "q", "documents": ["d"]})

    assert captured["timeout"] == 2.5, "必须使用实例级 REQUEST_TIMEOUT_SECONDS"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
