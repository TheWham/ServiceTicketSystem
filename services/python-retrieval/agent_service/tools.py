# -*- coding: utf-8 -*-
"""白名单工具集 + 派发。

能力边界（与 Java 版一致）：
- `query_my_tickets`：查「本人」工单。工单是 ticket-service 事实源，经其内部接口调用
  （架构 8.1，咨询域不跨库读 ticket 表）；creator 由 X-User-Id 绑定，模型无法查他人。
- `prepare_ticket`：只产建单草稿、**不落库**；员工确认后才由 Java 侧触发真正建单（人机回环）。
- `search_knowledge`：调 consultation-service 的知识搜索接口（只返回 PUBLISHED 当前版本）。

失败一律返回 `{"success": false, "error": ...}`（不抛），以 role="tool" 回传给模型触发反思自愈。
"""

from typing import Any, Dict, List
import uuid

import httpx

from . import config as acfg
from .contract import TicketDraft

_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}


class ToolContext:
    """一次 ReAct 调用的上下文：已认证主体 + 草稿收集 + 追踪 ID。"""

    __slots__ = ("user_id", "role", "draft", "request_id")

    def __init__(self, user_id: str, role: str, request_id: str = ""):
        self.user_id = user_id or ""
        self.role = role or ""
        self.draft: TicketDraft = None
        # 追踪 ID：优先透传上游（Java 侧 DependencyHttpClient 会带 X-Request-Id），
        # 缺失时本次 ReAct 自生成一个 —— 下游 consultation-service 的知识搜索接口
        # **强制要求**该头，缺失即 400 VALIDATION_ERROR（工具恒失败）。
        # 一次 run 内稳定，便于把同一轮里的多次工具调用串成一条链路。
        self.request_id = request_id or uuid.uuid4().hex

    def capture_draft(self, draft: TicketDraft) -> None:
        self.draft = draft


def tool_specs() -> List[Dict[str, Any]]:
    """OpenAI tools 数组（白名单工具的唯一来源）。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "在企业知识库中检索已发布（PUBLISHED）的 IT 办公知识条目，返回标题与摘要。"
                               "需要依据公司内部知识回答时使用。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "检索关键词，如“VPN 无法连接”"},
                        "categoryId": {"type": "string", "description": "可选，限定知识分类 ID"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_my_tickets",
                "description": "查询当前员工本人名下工单及其处理状态（如“我的工单什么状态”）。只能查本人数据。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "可选，按状态过滤：NEW/ASSIGNED/"
                                                                   "IN_PROGRESS/PENDING_ACCEPTANCE/COMPLETED/CLOSED"},
                        "limit": {"type": "integer", "description": "返回条数，默认 10，最大 50"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "prepare_ticket",
                "description": "把员工的 IT 故障/服务请求整理成工单草稿（标题、描述、可选分类与优先级）。"
                               "重要：只生成草稿，不会真正建单；草稿需员工确认后才会创建工单。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "工单标题，简洁概括问题"},
                        "description": {"type": "string", "description": "问题描述：现象、已做排查、影响范围"},
                        "category": {"type": "string", "description": "可选分类 ID，如 C_HW_PC/C_NET/C_SW/C_ACC"},
                        "priority": {"type": "string", "description": "可选优先级：HIGH/MEDIUM/LOW"},
                    },
                    "required": ["title", "description"],
                },
            },
        },
    ]


def dispatch(name: str, arguments: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """按名派发；未知工具返回结构化错误（不抛）。"""
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"success": False, "error": f"未知工具: {name}"}
    try:
        return handler(arguments or {}, ctx)
    except Exception as e:  # noqa: BLE001 —— 工具异常统一转结构化错误
        return {"success": False, "error": f"工具执行异常: {type(e).__name__}"}


# ---------------------------------------------------------------- 具体实现

def _http_get(url: str, params: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    # X-Request-Id 为下游强制头（consultation 的知识搜索缺它即 400），随 ctx 透传/生成。
    headers = {"X-User-Id": ctx.user_id, "X-User-Role": ctx.role,
               "X-Request-Id": ctx.request_id}
    with httpx.Client(timeout=acfg.TOOL_TIMEOUT) as client:
        resp = client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            # 带上响应体片段：缺头/校验失败这类问题只在 body 里说得清，
            # 否则上层只能看到一句 "HTTPStatusError"，排查成本很高。
            raise RuntimeError(
                f"下游 HTTP {resp.status_code}: {resp.text[:300]}")
        body = resp.json()
    # 两个下游的成功包络**不同**，不能统一按 code==0 判：
    #   ticket-service（Result）      -> {"code": 0, "msg": ...}
    #   consultation-service（21.1）  -> {"code": "SUCCESS", "message": ...}
    # 只认 int 0 会把知识搜索的每次成功都判成失败，且失败得毫无声响。
    code = body.get("code") if isinstance(body, dict) else None
    if code not in (0, "SUCCESS"):
        raise RuntimeError(f"下游业务错误 code={code!r}")
    return body


def _search_knowledge(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    base = acfg.KNOWLEDGE_SEARCH_BASE_URL
    if not base:
        return {"success": False, "error": "知识搜索未配置（KNOWLEDGE_SEARCH_BASE_URL）"}
    query = str(args.get("query") or "").strip()
    if not query:
        return {"success": False, "error": "缺少检索关键词 query"}
    params: Dict[str, Any] = {"query": query, "page": 1, "pageSize": acfg.SEARCH_MAX_RESULTS}
    category = str(args.get("categoryId") or "").strip()
    if category:
        params["category"] = category
    try:
        body = _http_get(base.rstrip("/") + "/api/v1/knowledge/search", params, ctx)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"知识搜索失败: {e}"}
    data = body.get("data") or {}
    items = data.get("items") or []
    return {"success": True, "total": data.get("total", len(items)),
            "items": [{"articleId": i.get("articleId"), "versionId": i.get("versionId"),
                       "title": i.get("title"), "summary": i.get("summary")} for i in items]}


def _query_my_tickets(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    base = acfg.TICKET_SERVICE_BASE_URL
    if not base:
        return {"success": False, "error": "工单系统未配置（TICKET_SERVICE_BASE_URL）"}
    try:
        limit = int(args.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    params: Dict[str, Any] = {"creator_id": ctx.user_id, "limit": max(1, min(50, limit))}
    status = str(args.get("status") or "").strip()
    if status:
        params["status"] = status
    try:
        body = _http_get(base.rstrip("/") + "/api/internal/tickets", params, ctx)
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"工单系统暂时不可用: {e}"}
    data = body.get("data")
    return {"success": True, "tickets": data if isinstance(data, list) else []}


def _prepare_ticket(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    title = str(args.get("title") or "").strip()[:acfg.DRAFT_TITLE_MAX]
    description = str(args.get("description") or "").strip()[:acfg.DRAFT_DESC_MAX]
    if not title:
        return {"success": False, "error": "缺少工单标题 title"}
    if not description:
        return {"success": False, "error": "缺少问题描述 description"}
    category = str(args.get("category") or "").strip() or None
    priority = str(args.get("priority") or "").strip().upper()
    if priority not in _PRIORITIES:
        priority = "MEDIUM"
    draft = TicketDraft(title=title, category=category, description=description, priority=priority)
    ctx.capture_draft(draft)
    out: Dict[str, Any] = {"success": True,
                           "note": "草稿已生成。请向员工展示草稿并说明需员工确认后才会真正建单。",
                           "title": title, "description": description, "priority": priority}
    if category:
        out["category"] = category
    return out


_HANDLERS = {
    "search_knowledge": _search_knowledge,
    "query_my_tickets": _query_my_tickets,
    "prepare_ticket": _prepare_ticket,
}