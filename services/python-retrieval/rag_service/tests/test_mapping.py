# -*- coding: utf-8 -*-
"""rag_service.mapping.build_response 的纯逻辑单测（不依赖向量库/网络）。

对照 Java 侧 RagServiceKnowledgeRetriever.parse 的强校验不变量：
- chunkId/articleId/versionId/indexVersion/title/snippet/content 均非空白
- 每条 indexVersion == versionId
- topScore == max(items[].score)，空结果时 topScore == 0.0
- score ∈ [0,1]
- ANSWER ⇔ reliable ⇔ suggestedRefusalReason 缺省；REFUSE 时 reason=LOW_CONFIDENCE 且 reliable=false
- publishedOnly 恒 true，domain 恒 OFFICE_IT
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_service.mapping import build_response  # noqa: E402


def _search_res(items, rejected=False):
    return {"final_results": items, "rejected": rejected}


def _item(child_id=None, chunk_id=None, parent_id="ITKB-ACC-002", wiki_id=None,
          parent_content="整卡全文" * 200, content="子块半截文本", rerank_score=0.81234,
          header_1="密码重置与过期处理", wiki_version="v1.0", wiki_category="账号与权限问题"):
    md = {"parent_id": parent_id, "wiki_version": wiki_version, "wiki_category": wiki_category}
    if child_id is not None:
        md["child_id"] = child_id
    if chunk_id is not None:
        md["chunk_id"] = chunk_id
    if wiki_id is not None:
        md["wiki_id"] = wiki_id
    if parent_content is not None:
        md["parent_content"] = parent_content
    if header_1 is not None:
        md["Header_1"] = header_1
    return {"content": content, "metadata": md, "rrf_score": 0.012, "rerank_score": rerank_score,
            "rrf_rank": 1, "rerank_rank": 1, "fused_score": 0.045}


MAPPING = {
    "ITKB-ACC-002": {"articleId": "art-1001", "versionId": "ver-2001",
                     "categoryId": "C_ACC", "wiki_version": "v1.0", "title": "密码重置与过期处理"},
}


def test_answer_path_full_mapping():
    resp = build_response(_search_res([_item(child_id="ITKB-ACC-002#c1")]),
                          wiki_mapping=MAPPING, request_category_id=None)
    assert resp.reliable is True
    assert resp.domain == "OFFICE_IT"
    assert resp.published_only is True
    assert resp.suggested_reply_type == "ANSWER"
    assert resp.suggested_refusal_reason is None
    it = resp.items[0]
    # chunkId 三级兜底：优先 child_id
    assert it.chunk_id == "ITKB-ACC-002#c1"
    # content 必须取整卡全文而非子块半截文本
    assert it.content == "整卡全文" * 200
    assert it.snippet == " ".join(it.content.split())[:1000]
    assert len(it.snippet) <= 1000
    # 映射命中：articleId/versionId 来自 mapping；indexVersion 恒等于 versionId
    assert it.article_id == "art-1001"
    assert it.version_id == "ver-2001"
    assert it.index_version == "ver-2001"
    assert it.category_id == "C_ACC"          # 未带过滤时回填 mapping 的 categoryId
    assert it.title == "密码重置与过期处理"
    # score = rerank 原始分（钳制+4 位小数），topScore = max(items.score)
    assert it.score == round(0.81234, 4)
    assert resp.top_score == max(i.score for i in resp.items)


def test_chunkid_fallback_chain():
    # 无 child_id → chunk_id；两者皆无 → parent_id
    r1 = build_response(_search_res([_item(child_id=None, chunk_id="ITKB-ACC-002_chunk_3")]),
                        wiki_mapping=MAPPING, request_category_id=None)
    assert r1.items[0].chunk_id == "ITKB-ACC-002_chunk_3"
    r2 = build_response(_search_res([_item(child_id=None, chunk_id=None)]),
                        wiki_mapping=MAPPING, request_category_id=None)
    assert r2.items[0].chunk_id == "ITKB-ACC-002"


def test_degraded_without_mapping():
    resp = build_response(_search_res([_item(child_id="ITKB-XXX-999#c0", parent_id="ITKB-XXX-999")]),
                          wiki_mapping={}, request_category_id=None)
    it = resp.items[0]
    assert it.article_id == "ITKB-XXX-999"        # 降级：articleId = parent_id
    assert it.version_id == "v1.0"                # 降级：versionId = wiki_version
    assert it.index_version == it.version_id
    assert it.category_id is None
    assert resp.reliable is True                  # 降级不等于拒答


def test_request_category_id_passthrough():
    resp = build_response(_search_res([_item(child_id="ITKB-ACC-002#c1")]),
                          wiki_mapping=MAPPING, request_category_id="C_NET")
    assert resp.items[0].category_id == "C_NET"   # 请求给了就原样回填


def test_score_clamped_to_unit_interval():
    resp = build_response(_search_res([_item(child_id="a#c0", rerank_score=1.23),
                                       _item(child_id="b#c0", rerank_score=-0.5)]),
                          wiki_mapping=MAPPING, request_category_id=None)
    assert resp.items[0].score == 1.0
    assert resp.items[1].score == 0.0
    assert resp.top_score == max(i.score for i in resp.items)


def test_rejected_and_empty_candidates_both_refuse():
    for res in (_search_res([], rejected=True), _search_res([], rejected=False)):
        resp = build_response(res, wiki_mapping=MAPPING, request_category_id=None)
        assert resp.items == []
        assert resp.reliable is False
        assert resp.suggested_reply_type == "REFUSE"
        assert resp.suggested_refusal_reason == "LOW_CONFIDENCE"
        assert resp.top_score == 0.0
        assert resp.domain == "OFFICE_IT"
        assert resp.published_only is True


def test_title_fallback_and_truncation():
    r = build_response(_search_res([_item(child_id="a#c0", header_1=None)]),
                       wiki_mapping=MAPPING, request_category_id=None)
    assert r.items[0].title == "ITKB-ACC-002"      # 缺 Header_1 → parent_id
    long_title = "标" * 300
    r2 = build_response(_search_res([_item(child_id="a#c0", header_1=long_title)]),
                        wiki_mapping=MAPPING, request_category_id=None)
    assert len(r2.items[0].title) == 200           # 对齐 Java titleOf 截断


def test_serialized_json_uses_camelcase_and_omits_null_reason():
    resp = build_response(_search_res([_item(child_id="ITKB-ACC-002#c1")]),
                          wiki_mapping=MAPPING, request_category_id=None)
    payload = json.loads(resp.model_dump_json(by_alias=True, exclude_none=True))
    assert set(payload) == {"items", "domain", "suggestedReplyType", "topScore", "reliable", "publishedOnly"}
    assert payload["suggestedReplyType"] == "ANSWER"
    assert "suggestedRefusalReason" not in payload
    item = payload["items"][0]
    for key in ("chunkId", "articleId", "versionId", "indexVersion", "title", "snippet", "content", "score"):
        assert key in item, key
    # Task 11：无图字段输入的条目，三键不得出场（老等价性）
    for key in ("graphExpanded", "expandedFrom", "relation"):
        assert key not in item, key
    assert item["indexVersion"] == item["versionId"]


def _expanded_item(from_id="ITKB-ACC-002", relation="RELATED", rerank_score=0.4,
                  parent_id="ITKB-PRN-002"):
    """Task 10 扩展条目形态：父块代表 + 顶层内部键 graph_expanded/graph_expanded_from/graph_relation。"""
    it = _item(child_id=None, chunk_id=None, parent_id=parent_id, rerank_score=rerank_score)
    it["graph_expanded"] = True
    it["graph_expanded_from"] = from_id
    it["graph_relation"] = relation
    return it


def test_graph_expanded_entries_mapped_to_contract_fields():
    """Task 11：内部三键 → 契约三字段（camelCase alias）；基础条目零感知。"""
    resp = build_response(_search_res([_item(child_id="ITKB-ACC-002#c1"),
                                       _expanded_item()]),
                          wiki_mapping=MAPPING, request_category_id=None)
    base, expanded = resp.items
    assert base.graph_expanded is None and base.expanded_from is None and base.relation is None
    assert expanded.graph_expanded is True
    assert expanded.expanded_from == "ITKB-ACC-002"
    assert expanded.relation == "RELATED"
    base_score = base.score
    payload = json.loads(resp.model_dump_json(by_alias=True, exclude_none=True))
    p_base, p_exp = payload["items"]
    assert "graphExpanded" not in p_base and "expandedFrom" not in p_base and "relation" not in p_base
    assert p_exp["graphExpanded"] is True
    assert p_exp["expandedFrom"] == "ITKB-ACC-002"
    assert p_exp["relation"] == "RELATED"
    assert p_base["score"] == base_score      # 基础条目 score 不受扩展条目影响


def test_topscore_computed_only_from_base_entries():
    """常规场景：基础 0.8 + 扩展 0.4（源×decay）→ topScore==0.8，扩展分不抬高。"""
    resp = build_response(_search_res([_item(child_id="b#c0", rerank_score=0.8),
                                       _expanded_item(rerank_score=0.4)]),
                          wiki_mapping=MAPPING, request_category_id=None)
    assert resp.top_score == 0.8
    assert resp.items[1].score == 0.4


def test_topscore_ignores_expanded_score_even_if_higher():
    """防御场景：扩展分并列/反超基础分（现实被 decay<1 排除）时 topScore 仍只取基础条目。"""
    resp = build_response(_search_res([_item(child_id="b#c0", rerank_score=0.4),
                                       _expanded_item(rerank_score=0.9)]),
                          wiki_mapping=MAPPING, request_category_id=None)
    base_scores = [i.score for i in resp.items if not i.graph_expanded]
    assert resp.top_score == max(base_scores) == 0.4


def test_all_expanded_without_base_refuses_without_crash():
    """防御场景：全扩展无基础（现实中 expander 只扩基础命中，不可能为空）→ top=0.0。
    带 reject_threshold 时走拒答路径；不带阈值也不崩、不拿扩展分充当 topScore。"""
    items = [_expanded_item(rerank_score=0.9),
             _expanded_item(rerank_score=0.7, parent_id="ITKB-NET-003")]
    resp = build_response(_search_res(items), wiki_mapping=MAPPING,
                          request_category_id=None, reject_threshold=0.3)
    assert resp.suggested_reply_type == "REFUSE"
    assert resp.suggested_refusal_reason == "LOW_CONFIDENCE"
    assert resp.items == []
    assert resp.top_score == 0.0
    resp2 = build_response(_search_res([_expanded_item(rerank_score=0.9)]),
                           wiki_mapping=MAPPING, request_category_id=None)
    assert resp2.top_score == 0.0            # 不以扩展分充当 topScore


def test_content_keeps_markdown_structure_while_snippet_collapses():
    """content 必须是 parent_content 原样（保留换行/缩进，供下游拼 grounding 提示），
    snippet 才做空白压缩 + 1000 截断（对齐 Java snippetOf 契约）。"""
    markdown = "# 标题\n\n## 步骤\n- 步骤1：重启\n- 步骤2：重连\n\n```bash\nnet stop spooler\n```\n"
    resp = build_response(
        _search_res([_item(child_id="ITKB-ACC-002#c1", parent_content=markdown)]),
        wiki_mapping=MAPPING, request_category_id=None)
    it = resp.items[0]
    assert it.content == markdown                       # 原样保留 Markdown 结构
    assert "\n" not in it.snippet                        # snippet 仍压缩为单行
    assert it.snippet == " ".join(markdown.split())[:1000]
    assert len(it.snippet) <= 1000


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
