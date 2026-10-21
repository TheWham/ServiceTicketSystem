# -*- coding: utf-8 -*-
"""版本消歧的 HTTP 出口（`POST /api/v1/policy/resolve`）与装配接线测试。

两件事分开验：
1. **装配接线**：`ServiceAssembly.resolve_policy` 必须真的走到 `PolicyResolver`，
   并与 `search()` 共用同一把检索锁（否则 rerank 限流预算会和普通检索互相挤占）；
2. **HTTP 形状**：四态原样透出、`UNDATED` 不是错误（HTTP 200 而非 4xx/5xx）、
   参数非法走统一包络 code=4000。

用桩装配（`create_app(assembly=...)` 已预留注入口），不加载真实向量库、不触网。
"""

import contextlib
import json
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_pipeline.policy import (  # noqa: E402
    NO_MATCH, RESOLVED, UNDATED, PolicyResolver)
from rag_service.app import create_app  # noqa: E402
from rag_service.assembly import ServiceAssembly  # noqa: E402


# ---------------------------------------------------------------- 替身

def chunk(article_id: str, *, title: str = "", version: str = "v1.0",
          status: str = "现行", effective: Optional[str] = None,
          replaces: Optional[List[str]] = None, score: float = 0.5) -> Dict[str, Any]:
    md: Dict[str, Any] = {
        "parent_id": article_id,
        "wiki_title": title or f"{article_id} 标题",
        "wiki_version": version,
        "wiki_status": status,
        "parent_content": "正文",
    }
    if effective is not None:
        md["wiki_effective_date"] = effective
    if replaces is not None:
        md["wiki_replaces"] = json.dumps(replaces, ensure_ascii=False)
    return {"metadata": md, "rerank_score": score, "content": "正文"}


class FakeRetriever:
    def __init__(self, results: List[Dict[str, Any]]):
        self._results = results
        self.calls: List[Dict[str, Any]] = []

    def hybrid_rerank_search(self, **kwargs):
        self.calls.append(kwargs)
        return {"final_results": list(self._results)}


ACC_CHAIN = [
    chunk("ITKB-ACC-001", title="域账号锁定排查与解锁处理", version="v1.0",
          effective="2024-03-01", replaces=["ITKB-LEG-ACC-001"], score=0.91),
    chunk("ITKB-LEG-ACC-001", title="域账号锁定处理（旧版，已废止）", version="v0.9",
          status="已废止", effective="2022-01-01", score=0.55),
]


class StubAssembly:
    """只实现出口用到的那一个方法，把 HTTP 层与装配层解耦。"""

    def __init__(self, resolution=None, error: Optional[Exception] = None):
        self._resolution = resolution
        self._error = error
        self.calls: List[Dict[str, Any]] = []

    def resolve_policy(self, query, at=None, top_k=8):
        self.calls.append({"query": query, "at": at, "top_k": top_k})
        if self._error:
            raise self._error
        return self._resolution


@contextlib.contextmanager
def client_for(assembly):
    """必须用 with：assembly 是在 lifespan 里注入 app.state 的，不跑 lifespan 就取不到。

    `raise_server_exceptions=False` 让未预期异常走 app 注册的 500 处理器，
    而不是被 TestClient 直接抛回测试——否则测不了「兜底 5000」这条映射。
    """
    with TestClient(create_app(assembly=assembly), raise_server_exceptions=False) as client:
        yield client


def post(assembly, payload):
    with client_for(assembly) as client:
        return client.post("/api/v1/policy/resolve", json=payload)


def resolved_resolution():
    return PolicyResolver(FakeRetriever(ACC_CHAIN), corpus_docs=[]) \
        .resolve("域账号锁定", at="2024-06-01")


def undated_resolution():
    return PolicyResolver(FakeRetriever([chunk("ITKB-HW-002", score=0.8)]), corpus_docs=[]) \
        .resolve("打印机脱机", at="2024-06-01")


# ---------------------------------------------------------------- 装配接线

def _bare_assembly(results: List[Dict[str, Any]]) -> ServiceAssembly:
    """绕过 __init__（不加载向量库），只为测 resolve_policy 的方法体。"""
    asm = ServiceAssembly.__new__(ServiceAssembly)
    asm.retriever = FakeRetriever(results)
    asm.corpus = []
    asm.serialize_search = True
    asm.lock_wait_seconds = 5.0
    asm._lock = threading.Lock()
    asm._policy_resolver = None
    return asm


def test_assembly_resolve_policy_returns_resolution():
    asm = _bare_assembly(ACC_CHAIN)
    res = asm.resolve_policy("域账号锁定", at="2024-01-15")
    assert res.status == RESOLVED
    assert res.article_id == "ITKB-LEG-ACC-001"


def test_assembly_reuses_one_resolver_across_calls():
    asm = _bare_assembly(ACC_CHAIN)
    asm.resolve_policy("域账号锁定", at="2024-01-15")
    first = asm._policy_resolver
    asm.resolve_policy("域账号锁定", at="2024-06-01")
    assert asm._policy_resolver is first, "解析器应复用，不该每次重建"


def test_assembly_releases_the_search_lock_after_resolve():
    asm = _bare_assembly(ACC_CHAIN)
    asm.resolve_policy("域账号锁定", at="2024-06-01")
    assert not asm._lock.locked(), "检索锁必须释放，否则后续检索会全部 5031"


def test_assembly_releases_the_search_lock_even_on_failure():
    class Boom:
        def hybrid_rerank_search(self, **kwargs):
            raise RuntimeError("检索炸了")

    asm = _bare_assembly([])
    asm.retriever = Boom()
    with pytest.raises(RuntimeError):
        asm.resolve_policy("任意", at="2024-06-01")
    assert not asm._lock.locked(), "异常路径也必须释放锁"


# ---------------------------------------------------------------- HTTP 形状

def test_resolve_endpoint_returns_camel_case_payload():
    stub = StubAssembly(resolved_resolution())
    resp = post(stub, {"query": "域账号锁定", "at": "2024-06-01"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["status"] == RESOLVED
    assert data["articleId"] == "ITKB-ACC-001"
    assert data["version"] == "v1.0"
    assert data["effectiveDate"] == "2024-03-01"
    assert data["citation"] == "[来源: ITKB-ACC-001@v1.0 《域账号锁定排查与解锁处理》]"
    assert data["replacedArticles"] == ["ITKB-LEG-ACC-001"]
    assert isinstance(data["chain"], list) and data["chain"]
    assert stub.calls == [{"query": "域账号锁定", "at": "2024-06-01", "top_k": 8}]


def test_undated_is_a_normal_answer_not_an_error():
    """「没有生效日期、无法判定」是结论，不是失败——必须是 200 而不是 4xx/5xx。"""
    stub = StubAssembly(undated_resolution())
    resp = post(stub, {"query": "打印机脱机"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == UNDATED
    assert body["data"]["citation"] is None
    assert "不猜" in body["data"]["reason"]


def test_no_match_is_also_a_normal_answer():
    stub = StubAssembly(PolicyResolver(FakeRetriever([]), corpus_docs=[])
                        .resolve("查不到", at="2024-06-01"))
    resp = post(stub, {"query": "查不到"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == NO_MATCH


def test_at_is_optional_and_forwarded_as_none():
    stub = StubAssembly(resolved_resolution())
    resp = post(stub, {"query": "域账号锁定"})
    assert resp.status_code == 200
    assert stub.calls[0]["at"] is None


def test_topk_alias_is_accepted_and_forwarded():
    stub = StubAssembly(resolved_resolution())
    resp = post(stub, {"query": "域账号锁定", "topK": 3})
    assert resp.status_code == 200
    assert stub.calls[0]["top_k"] == 3


def test_missing_query_is_rejected_with_4000():
    stub = StubAssembly(resolved_resolution())
    resp = post(stub, {})
    assert resp.status_code == 400
    assert resp.json()["code"] == 4000
    assert stub.calls == [], "参数非法时不该触达装配层"


def test_blank_query_is_rejected_with_4000():
    stub = StubAssembly(resolved_resolution())
    resp = post(stub, {"query": ""})
    assert resp.status_code == 400
    assert resp.json()["code"] == 4000


def test_topk_out_of_range_is_rejected_with_4000():
    stub = StubAssembly(resolved_resolution())
    resp = post(stub, {"query": "域账号锁定", "topK": 99})
    assert resp.status_code == 400
    assert resp.json()["code"] == 4000


def test_lock_busy_maps_to_5031():
    from rag_service.assembly import LockBusy

    stub = StubAssembly(error=LockBusy("检索锁等待超过 1.0s"))
    resp = post(stub, {"query": "域账号锁定"})
    assert resp.status_code == 503
    assert resp.json()["code"] == 5031


def test_unexpected_error_maps_to_5000():
    stub = StubAssembly(error=RuntimeError("意外炸了"))
    resp = post(stub, {"query": "域账号锁定"})
    assert resp.status_code == 500
    assert resp.json()["code"] == 5000