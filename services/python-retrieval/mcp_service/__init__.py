# -*- coding: utf-8 -*-
"""IT 服务工单与知识咨询 MCP Service 模块。"""

from .contract import (
    CategoryItem,
    TicketDraft,
    ToolResultEnvelope,
    VALID_CATEGORIES,
    VALID_PRIORITIES,
)
from .engine import FastMCP, ZeroDepFastMCP
from .server import (
    mcp,
    prepare_ticket_draft,
    query_my_tickets,
    search_knowledge,
    get_categories_tree,
    get_system_status,
    it_troubleshoot_prompt,
    ticket_draft_confirm_prompt,
)

__all__ = [
    "mcp",
    "FastMCP",
    "ZeroDepFastMCP",
    "TicketDraft",
    "CategoryItem",
    "ToolResultEnvelope",
    "VALID_CATEGORIES",
    "VALID_PRIORITIES",
    "prepare_ticket_draft",
    "query_my_tickets",
    "search_knowledge",
    "get_categories_tree",
    "get_system_status",
    "it_troubleshoot_prompt",
    "ticket_draft_confirm_prompt",
]
