# -*- coding: utf-8 -*-
import json
import pytest
from mcp_service.server import (
    mcp,
    prepare_ticket_draft,
    get_categories_tree,
    get_system_status,
    it_troubleshoot_prompt,
    ticket_draft_confirm_prompt,
    query_my_tickets,
    search_knowledge,
)

def test_prepare_ticket_draft_valid():
    res = prepare_ticket_draft("网络无法连接", "工位网口亮红灯，无法上网", "C_NET", "HIGH")
    assert "工单草稿已就绪" in res
    assert "网络无法连接" in res
    assert "C_NET" in res
    assert "需员工在前端确认" in res

def test_prepare_ticket_draft_fallback():
    res = prepare_ticket_draft("未知问题", "不知道什么分类", "UNKNOWN_CATEGORY", "INVALID_PRIO")
    assert "工单草稿已就绪" in res
    assert "C_OTH" in res
    assert "MEDIUM" in res

def test_resource_categories_tree():
    raw_json = get_categories_tree()
    assert "C_HW_PC" in raw_json
    assert "打印机与外设" in raw_json
    parsed = json.loads(raw_json)
    assert len(parsed["categories"]) >= 5

def test_resource_system_status():
    status_raw = get_system_status()
    assert "server_name" in status_raw
    parsed = json.loads(status_raw)
    assert parsed["server_name"] == "IT-Ticket-Service-Server"
    assert "services" in parsed

def test_prompt_troubleshoot():
    # 显式参数
    prompt = it_troubleshoot_prompt("VPN")
    assert "VPN" in prompt
    assert "排查" in prompt

    # 默认/空参调用兼容
    default_prompt = it_troubleshoot_prompt()
    assert "排查" in default_prompt
    assert "未指定故障" in default_prompt

def test_prompt_draft_confirm():
    # 显式参数
    prompt = ticket_draft_confirm_prompt("鼠标失灵", "无法点击左键", "C_HW_PC", "LOW")
    assert "鼠标失灵" in prompt
    assert "C_HW_PC" in prompt

    # 默认/空参调用兼容
    default_prompt = ticket_draft_confirm_prompt()
    assert "系统故障" in default_prompt

def test_live_or_graceful_tickets():
    # 测试连接 8201 真实服务或异常返回 (不抛未捕获异常)
    res = query_my_tickets(user_id="U1001", limit=3)
    assert isinstance(res, str)
    assert len(res) > 0

def test_live_or_graceful_knowledge():
    # 测试连接 8301 真实服务或异常返回 (不抛未捕获异常)
    res = search_knowledge(query="VPN", limit=2)
    assert isinstance(res, str)
    assert len(res) > 0
