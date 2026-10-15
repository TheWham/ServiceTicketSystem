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


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
