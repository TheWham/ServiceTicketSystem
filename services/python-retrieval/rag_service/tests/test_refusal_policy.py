# -*- coding: utf-8 -*-
"""服务层拒答判定的守护测试（含 rerank 降级场景）。

背景（实测）：网关 429 限流打满在线收紧后的预算（1.5s/8 次）时，rerank 降级为
启发式打分，内核 `hybrid.py` 的拒答门因 `last_used_remote=False` 被跳过 ——
于是"知识库未记载"的对抗题会被正常作答，防幻觉底线失守。

服务层裁定：拒答不以"是否走了远程"为条件，统一按 reject_threshold 判定：
  refuse ⇔ 内核已拒答 ∨ 无候选 ∨ max(score) < reject_threshold
远程成功时与内核行为一致（Day14 基线复现）；降级时依然守住阈值。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rag_service.mapping import build_response  # noqa: E402


def _res(items, rejected=False, rerank_remote=True):
    return {"final_results": items, "rejected": rejected, "rerank_remote": rerank_remote}


def _item(score, child_id="ITKB-ACC-002#c1", parent_id="ITKB-ACC-002"):
    return {"content": "子块", "metadata": {"child_id": child_id, "parent_id": parent_id,
                                            "parent_content": "整卡全文" * 200,
                                            "wiki_version": "v1.0", "Header_1": "标题"},
            "rerank_score": score}


def test_degraded_low_score_is_refused():
    """降级（启发式）低分：必须拒答——修复前会因 last_used_remote=False 被放行。"""
    resp = build_response(_res([_item(0.15)], rerank_remote=False),
                          wiki_mapping={}, request_category_id=None, reject_threshold=0.40)
    assert resp.items == []
    assert resp.reliable is False
    assert resp.suggested_reply_type == "REFUSE"
    assert resp.suggested_refusal_reason == "LOW_CONFIDENCE"
    assert resp.top_score == 0.0


def test_degraded_high_score_still_answered():
    """降级但启发式高分（本语料正样本常见 0.99）：仍作答，避免限流时全量误拒。"""
    resp = build_response(_res([_item(0.99)], rerank_remote=False),
                          wiki_mapping={}, request_category_id=None, reject_threshold=0.40)
    assert resp.suggested_reply_type == "ANSWER"
    assert resp.reliable is True
    assert resp.top_score == 0.99


def test_remote_low_score_refused_even_if_kernel_did_not_reject():
    """内核未拒答但分数低于阈值：服务层兜底拒答（防御性，正常由内核处理）。"""
    resp = build_response(_res([_item(0.30)], rejected=False, rerank_remote=True),
                          wiki_mapping={}, request_category_id=None, reject_threshold=0.40)
    assert resp.suggested_reply_type == "REFUSE"
    assert resp.items == []


def test_threshold_none_disables_service_level_rejection():
    resp = build_response(_res([_item(0.30)], rerank_remote=True),
                          wiki_mapping={}, request_category_id=None, reject_threshold=None)
    assert resp.suggested_reply_type == "ANSWER"
    assert len(resp.items) == 1


def test_remote_answer_path_unchanged():
    resp = build_response(_res([_item(0.78)], rerank_remote=True),
                          wiki_mapping={}, request_category_id=None, reject_threshold=0.40)
    assert resp.suggested_reply_type == "ANSWER"
    assert resp.top_score == 0.78


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
