# -*- coding: utf-8 -*-
"""生产级 IT 服务工单与知识咨询 FastMCP Server 实现。

发布三大核心原语：
1. Tools:
   - search_knowledge: 企业知识库排障指引检索 (调 consultation-service:8301)
   - query_my_tickets: 员工名下工单进度查询 (调 ticket-service:8201)
   - prepare_ticket_draft: 故障事实整理为规范工单草稿 (本地校验，不落库)
2. Resources:
   - it://categories/tree: 官方有效末级分类字典树
   - it://system/status: 底层微服务连通性与运行时探针
3. Prompts:
   - it_troubleshoot_prompt: 标准 IT 故障排查工作流引导模版
   - ticket_draft_confirm_prompt: 建单前人机回环要素复核模版
"""
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import httpx

if __package__ or "." in __name__:
    from .contract import VALID_CATEGORIES, VALID_PRIORITIES, TicketDraft
    from .engine import FastMCP
else:
    # 直接作为脚本执行时的自适应路径解析
    pkg_dir = Path(__file__).resolve().parent
    if str(pkg_dir.parent) not in sys.path:
        sys.path.insert(0, str(pkg_dir.parent))
    from mcp_service.contract import VALID_CATEGORIES, VALID_PRIORITIES, TicketDraft
    from mcp_service.engine import FastMCP

log = logging.getLogger(__name__)

# 初始化 FastMCP Server
mcp = FastMCP("IT-Ticket-Service-Server")

# 微服务基址与身份默认值配置
TICKET_SERVICE_BASE_URL = os.environ.get("TICKET_SERVICE_BASE_URL", "http://127.0.0.1:8201")
KNOWLEDGE_SEARCH_BASE_URL = os.environ.get("KNOWLEDGE_SEARCH_BASE_URL", "http://127.0.0.1:8301")
DEFAULT_USER_ID = os.environ.get("MCP_USER_ID", "U_EMP01")
DEFAULT_USER_ROLE = os.environ.get("MCP_USER_ROLE", "EMPLOYEE")
HTTP_TIMEOUT = float(os.environ.get("MCP_HTTP_TIMEOUT", "10.0"))


def _build_headers(user_id: Optional[str] = None) -> Dict[str, str]:
    """构建符合企业微服务安全规范的身份与链路追踪头。"""
    actual_user_id = (user_id or DEFAULT_USER_ID).strip()
    return {
        "X-User-Id": actual_user_id,
        "X-User-Role": DEFAULT_USER_ROLE,
        "X-Request-Id": f"mcp-{uuid.uuid4().hex[:12]}",
    }


def _http_get(url: str, params: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """执行底层 HTTP GET 调用，保留真实错误，不静默回退。"""
    headers = _build_headers(user_id)
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        resp = client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        body = resp.json()

    code = body.get("code") if isinstance(body, dict) else None
    if code not in (0, "SUCCESS"):
        raise RuntimeError(f"业务响应异常 code={code!r}, msg={body.get('message') or body.get('msg')}")
    return body


# ==============================================================================
# 原语 1: 标准 Tools (操作类工具)
# ==============================================================================

@mcp.tool()
def search_knowledge(query: str, category_id: Optional[str] = None, limit: int = 5) -> str:
    """在企业知识库中检索已发布(PUBLISHED)的 IT 办公知识条目与排障指南。

    :param query: 检索关键词，如 'VPN 无法连接' 或 '打印机卡纸'
    :param category_id: 可选，限定检索分类 ID，如 'C_NET'
    :param limit: 可选，返回最大条数，默认 5，最大 20
    """
    q = (query or "").strip()
    if not q:
        return "❌ 检索失败：缺少必要查询关键词 query。"

    page_size = max(1, min(20, limit or 5))
    params: Dict[str, Any] = {"query": q, "page": 1, "pageSize": page_size}
    if category_id:
        params["category"] = category_id.strip()

    target_url = KNOWLEDGE_SEARCH_BASE_URL.rstrip("/") + "/api/v1/knowledge/search"
    try:
        body = _http_get(target_url, params)
    except Exception as e:
        log.warning("search_knowledge failed: %s", e)
        return f"❌ 知识库检索失败（consultation-service 8301 异常）：{e}"

    data = body.get("data") or {}
    items = data.get("items") or []
    if not items:
        return f"🔍 知识库未检索到与「{q}」直接相关的公开指引（建议检查关键词或申请人工建单支持）。"

    lines = [f"📚 【知识库排障指引】共匹配到 {len(items)} 条相关条目："]
    for idx, item in enumerate(items, start=1):
        title = item.get("title", "未命名文档")
        summary = item.get("summary", "暂无摘要")
        art_id = item.get("articleId", "")
        lines.append(f"{idx}. **{title}** (ID: {art_id})\n   - 核心要点: {summary}")
    return "\n".join(lines)


@mcp.tool()
def query_my_tickets(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
    created_after: Optional[str] = None,
    category: Optional[str] = None,
) -> str:
    """查询员工本人名下提交的 IT 工单流水及其最新处理进度。

    :param user_id: 可选，员工工号（缺省时从环境变量上下文获取当前员工身份）
    :param status: 可选，按状态过滤：NEW/ASSIGNED/IN_PROGRESS/PENDING_ACCEPTANCE/COMPLETED/CLOSED
    :param limit: 可选，返回最大条数，默认 10，最大 50
    :param created_after: 可选，只查该日期（含）之后创建的工单，ISO 格式 YYYY-MM-DD
    :param category: 可选，按分类 ID 过滤，如 'C_HW_PC'
    """
    actual_user_id = (user_id or DEFAULT_USER_ID).strip()
    fetch_limit = max(1, min(50, limit or 10))

    params: Dict[str, Any] = {"creator_id": actual_user_id, "limit": fetch_limit}
    if status:
        params["status"] = status.strip().upper()
    if created_after:
        params["created_after"] = created_after.strip()
    if category:
        params["category"] = category.strip()

    target_url = TICKET_SERVICE_BASE_URL.rstrip("/") + "/api/internal/tickets"
    try:
        body = _http_get(target_url, params, user_id=actual_user_id)
    except Exception as e:
        log.warning("query_my_tickets failed: %s", e)
        return f"❌ 工单系统查询失败（ticket-service 8201 异常）：{e}"

    tickets = body.get("data") or []
    if not isinstance(tickets, list) or not tickets:
        return f"📋 员工 [{actual_user_id}] 名下当前暂无符合条件的工单记录。"

    lines = [f"🎫 员工 [{actual_user_id}] 名下最近工单明细（共 {len(tickets)} 条）："]
    for t in tickets:
        t_id = t.get("ticketId") or t.get("ticket_id") or t.get("id", "未知编号")
        t_title = t.get("title", "无标题")
        t_status = t.get("status", "UNKNOWN")
        t_prio = t.get("priority", "NORMAL")
        t_cat = t.get("categoryName") or t.get("category_name") or t.get("category", "默认")
        lines.append(f"- 【{t_status}】[{t_prio}] #{t_id} {t_title} (分类: {t_cat})")
    return "\n".join(lines)


@mcp.tool()
def prepare_ticket_draft(
    title: str,
    description: str,
    category: Optional[str] = None,
    priority: Optional[str] = "MEDIUM",
) -> str:
    """将员工反映的 IT 故障整理为标准规范的工单草稿。重要：本工具只生成草稿供复核，不会直接落库建单。

    :param title: 工单简明标题，只能取自员工消息中的事实短语
    :param description: 问题详细描述与现象
    :param category: 可选分类 ID：C_HW_PC/C_HW_PR/C_SW/C_NET/C_ACC/C_OTH（未知可省略）
    :param priority: 可选优先级：HIGH/MEDIUM/LOW，默认为 MEDIUM
    """
    draft = TicketDraft(
        title=title,
        description=description,
        category=category or "C_OTH",
        priority=priority or "MEDIUM",
    )
    draft_dict = draft.to_dict()

    return (
        f"📝 【工单草稿已就绪（待员工复核）】\n"
        f"--------------------------------------------------\n"
        f"📌 标题: {draft_dict['title']}\n"
        f"🏷️ 分类: {draft_dict['category']} ({draft_dict['category_name']})\n"
        f"⚡ 优先级: {draft_dict['priority']}\n"
        f"📄 描述: {draft_dict['description']}\n"
        f"--------------------------------------------------\n"
        f"⚠️ 安全防线提示：本单据尚未提交至企业数据库。需员工在前端确认无误后方可正式建单。"
    )


# ==============================================================================
# 原语 2: 标准 Resources (只读资源通道)
# ==============================================================================

@mcp.resource("it://categories/tree")
def get_categories_tree() -> str:
    """企业官方启用的 IT 服务分类字典树与末级分类说明。"""
    categories = [
        {"id": c["id"], "name": c["name"], "description": c["description"]}
        for c in VALID_CATEGORIES.values()
    ]
    return json.dumps({"categories": categories}, ensure_ascii=False, indent=2)


@mcp.resource("it://system/status")
def get_system_status() -> str:
    """探测底层微服务连通性与当前运行环境状态。"""
    services_state: Dict[str, Any] = {}

    # 探测 8201 ticket-service
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{TICKET_SERVICE_BASE_URL.rstrip('/')}/actuator/health")
            services_state["ticket_service_8201"] = {
                "url": TICKET_SERVICE_BASE_URL,
                "status": "UP" if resp.status_code in (200, 401) else f"STATUS_{resp.status_code}",
            }
    except Exception as e:
        services_state["ticket_service_8201"] = {"url": TICKET_SERVICE_BASE_URL, "status": "DOWN", "error": str(e)}

    # 探测 8301 consultation-service
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{KNOWLEDGE_SEARCH_BASE_URL.rstrip('/')}/actuator/health")
            services_state["consultation_service_8301"] = {
                "url": KNOWLEDGE_SEARCH_BASE_URL,
                "status": "UP" if resp.status_code in (200, 401) else f"STATUS_{resp.status_code}",
            }
    except Exception as e:
        services_state["consultation_service_8301"] = {"url": KNOWLEDGE_SEARCH_BASE_URL, "status": "DOWN", "error": str(e)}

    status_report = {
        "server_name": "IT-Ticket-Service-Server",
        "current_user_context": {
            "user_id": DEFAULT_USER_ID,
            "role": DEFAULT_USER_ROLE,
        },
        "services": services_state,
    }
    return json.dumps(status_report, ensure_ascii=False, indent=2)


# ==============================================================================
# 原语 3: 标准 Prompts (专业指令模版)
# ==============================================================================

@mcp.prompt()
def it_troubleshoot_prompt(issue_keyword: str = "未指定故障/常见问题") -> str:
    """面向 IT 故障排查的标准化引导模版。

    :param issue_keyword: 故障关键词（如 VPN、网络连接、打印机、账号登录）
    """
    return f"""你是一位企业 IT 服务台的资深排障专家。当前员工遇到了涉及【{issue_keyword}】的故障。
请遵循以下排查准则作答：
1. 先根据内部知识库（search_knowledge）核实企业官方解决指引；
2. 指导员工执行低风险排查步骤（如检查网络指示灯、重启服务、确认VPN配置）；
3. 严格禁止索取用户密码、验证码，严禁指导高风险提权命令；
4. 若自助排查无法解决，提示员工可通过 prepare_ticket_draft 整理工单草稿进行建单提交流转。"""


@mcp.prompt()
def ticket_draft_confirm_prompt(
    title: str = "系统故障",
    description: str = "用户遇到未知异常，待补充具体细节",
    category: Optional[str] = None,
    priority: Optional[str] = "MEDIUM",
) -> str:
    """人机回环（HITL）工单建单前向员工确认要素的交互模版。

    :param title: 工单简明标题
    :param description: 故障详细描述
    :param category: 建议分类编码 (如 C_NET, C_HW_PC)
    :param priority: 优先级 (LOW, MEDIUM, HIGH, URGENT)
    """
    return f"""请以礼貌、严谨的 IT 服务台语气，为员工确认即将提交的工单草稿：
- 工单标题：{title}
- 问题描述：{description}
- 建议分类：{category or '其他办公支持'}
- 优先级：{priority or 'MEDIUM'}

请向员工明确询问：
“您好，已为您整理好上述工单草稿。请核对信息是否准确？确认无误请回复‘确认建单’，我将为您正式生成工单并派发给对应工程师处理。”"""


# ==============================================================================
# 服务入口：支持直接作为独立脚本运行 (python mcp_service/server.py)
# ==============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")

