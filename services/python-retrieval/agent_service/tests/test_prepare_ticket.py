# -*- coding: utf-8 -*-
"""建单草稿字段抽取回归：员工明确给出标题/内容时，不得把整段上下文写进 description。"""

from agent_service import tools


def _ctx(question: str) -> tools.ToolContext:
    return tools.ToolContext("U1", "EMPLOYEE", question=question)


def test_prepare_ticket_extracts_explicit_title_and_content(monkeypatch):
    monkeypatch.setattr(tools, "_leaf_category_ids", lambda ctx: {"C_OTH"})
    question = "新建一个工单 标题为电脑蓝屏 内容为电脑蓝屏"
    ctx = _ctx(question)

    result = tools._prepare_ticket(
        {
            "title": question,
            "description": question,
            "category": "C_OTH",
            "priority": "MEDIUM",
        },
        ctx,
    )

    assert result["success"] is True
    assert result["title"] == "电脑蓝屏"
    assert result["description"] == "电脑蓝屏"
    assert ctx.draft is not None
    assert ctx.draft.title == "电脑蓝屏"
    assert ctx.draft.description == "电脑蓝屏"


def test_prepare_ticket_extracts_explicit_fields_with_chinese_punctuation(monkeypatch):
    monkeypatch.setattr(tools, "_leaf_category_ids", lambda ctx: {"C_OTH"})
    ctx = _ctx("新建工单，标题：电脑蓝屏，内容：电脑蓝屏。")

    result = tools._prepare_ticket(
        {"title": "电脑蓝屏", "description": "电脑蓝屏", "category": "C_OTH"},
        ctx,
    )

    assert result["success"] is True
    assert result["title"] == "电脑蓝屏"
    assert result["description"] == "电脑蓝屏"


def test_prepare_ticket_rejects_full_message_when_no_explicit_fields(monkeypatch):
    monkeypatch.setattr(tools, "_leaf_category_ids", lambda ctx: {"C_OTH"})
    question = "帮我建个工单，电脑蓝屏"
    ctx = _ctx(question)

    result = tools._prepare_ticket(
        {"title": "电脑蓝屏", "description": question, "category": "C_OTH"},
        ctx,
    )

    assert result["success"] is False
    assert "整段员工消息" in result["error"]
    assert ctx.draft is None
