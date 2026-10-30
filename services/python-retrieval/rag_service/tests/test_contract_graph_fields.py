# -*- coding: utf-8 -*-
"""RetrievedChunk 图扩展三字段的契约级用例（Task 11）。

对照 Java 侧 consultation `RagServiceKnowledgeRetriever.parse` 的强校验语义：
- `graphExpanded` / `expandedFrom` / `relation` 为可选字段，alias 输出 camelCase；
- 三字段缺省 None 时，经 app.py 的 `model_dump(by_alias=True, exclude_none=True)`
  序列化后**不在响应中**（老生产者/老消费者零感知）；
- score 的 [0,1] 约束不因追加字段而弱化；
- `tools/check_contract.py` 是需起服务的 HTTP 黑盒脚本，单测对其正向断言段的
  图扩展新断言只做**源级存在性守护**（不起服务就无法运行黑盒脚本本身）。
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pydantic import ValidationError  # noqa: E402

from rag_service.contract import RetrievedChunk  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def _chunk(**overrides):
    base = dict(
        chunk_id="ITKB-ACC-002#c1", article_id="art-1001", version_id="ver-2001",
        index_version="ver-2001", title="密码重置", snippet="片段", content="全文",
        score=0.82,
    )
    base.update(overrides)
    return RetrievedChunk(**base)


def test_graph_fields_serialized_with_aliases():
    """Task 11 契约三字段：按 camelCase alias 出场，值原样传递。"""
    it = _chunk(graph_expanded=True, expanded_from="ITKB-ACC-002", relation="RELATED")
    payload = json.loads(it.model_dump_json(by_alias=True))
    assert payload["graphExpanded"] is True
    assert payload["expandedFrom"] == "ITKB-ACC-002"
    assert payload["relation"] == "RELATED"


def test_graph_fields_absent_from_wire_when_unset():
    """缺省 None + exclude_none → 三键完全不在序列化结果中（老等价性）。"""
    payload = json.loads(_chunk().model_dump_json(by_alias=True, exclude_none=True))
    assert "graphExpanded" not in payload
    assert "expandedFrom" not in payload
    assert "relation" not in payload


def test_graph_fields_constructible_by_alias():
    """populate_by_name：alias（Java/HTTP 侧形态）可直接构造，字段名也可。"""
    it = RetrievedChunk(
        chunkId="ITKB-PRN-002", articleId="art-9002", versionId="ver-2002",
        indexVersion="ver-2002", title="打印机脱机", snippet="片段", content="全文",
        score=0.5,
        graphExpanded=True, expandedFrom="ITKB-ACC-002", relation="PROCESS_APPLIES",
    )
    assert it.graph_expanded is True
    assert it.expanded_from == "ITKB-ACC-002"
    assert it.relation == "PROCESS_APPLIES"


def test_score_bounds_still_enforced():
    """score ge=0/le=1 约束仍生效（追加字段不得弱化既有校验）。"""
    for bad in (1.5, -0.01):
        with pytest.raises(ValidationError):
            _chunk(score=bad)


def test_check_contract_positive_section_guards_graph_fields():
    """check_contract.py 正向断言段的图扩展守护存在性（HTTP 黑盒，源级守护）：
    若 item 含 graphExpanded 则 expandedFrom/relation 非空且 topScore==max(基础条目 score)。"""
    src = (REPO_ROOT / "tools" / "check_contract.py").read_text(encoding="utf-8")
    assert "graphExpanded" in src, "正向断言段须识别扩展条目"
    assert "expandedFrom" in src, "扩展条目须自证来源"
    assert "max(基础条目 score)" in src, "topScore 只统计基础条目"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
