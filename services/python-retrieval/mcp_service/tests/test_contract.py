# -*- coding: utf-8 -*-
import pytest
from mcp_service.contract import (
    VALID_CATEGORIES,
    VALID_PRIORITIES,
    TicketDraft,
    ToolResultEnvelope,
)

def test_valid_categories_content():
    assert "C_HW_PC" in VALID_CATEGORIES
    assert "C_SW" in VALID_CATEGORIES
    assert "C_NET" in VALID_CATEGORIES
    assert "C_OTH" in VALID_CATEGORIES
    assert VALID_CATEGORIES["C_HW_PC"]["name"] == "PC与电脑硬件"

def test_ticket_draft_validation():
    draft = TicketDraft(title="测试标题", description="测试问题描述", category="C_HW_PC", priority="HIGH")
    assert draft.category == "C_HW_PC"
    assert draft.priority == "HIGH"

def test_ticket_draft_invalid_fallback():
    draft = TicketDraft(title="测试", description="描述", category="UNKNOWN_CAT", priority="URGENT")
    assert draft.category == "C_OTH"
    assert draft.priority == "MEDIUM"

def test_tool_result_envelope_to_text():
    env = ToolResultEnvelope(success=True, data={"ticket_id": "T123"})
    assert "ticket_id" in env.to_text()
    assert env.success is True
