# -*- coding: utf-8 -*-
import json
import pytest
from mcp_service.client import ITServiceMCPClient

def test_client_in_process_mode():
    client = ITServiceMCPClient(mode="in_process")

    # 1. 发现工具
    tools = client.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "search_knowledge" in tool_names
    assert "query_my_tickets" in tool_names
    assert "prepare_ticket_draft" in tool_names

    # 2. 导出为 OpenAI Tools 结构
    openai_tools = client.to_openai_tools()
    assert len(openai_tools) >= 3
    assert openai_tools[0]["type"] == "function"
    assert "name" in openai_tools[0]["function"]
    assert "parameters" in openai_tools[0]["function"]

    # 3. 进程内直调工具
    draft_res = client.call_tool("prepare_ticket_draft", {
        "title": "显示器黑屏",
        "description": "电源灯亮但屏幕无显示",
        "category": "C_HW_PC",
        "priority": "MEDIUM",
    })
    assert "工单草稿已就绪" in draft_res
    assert "显示器黑屏" in draft_res

    # 4. 读取资源
    cat_res = client.read_resource("it://categories/tree")
    assert "C_HW_PC" in cat_res

    # 5. 获取提示词
    prompt_res = client.get_prompt("it_troubleshoot_prompt", {"issue_keyword": "VPN"})
    assert "VPN" in prompt_res

def test_client_stdio_handshake_and_call():
    # 测试 stdio 子进程管道模式
    client = ITServiceMCPClient(mode="stdio")
    try:
        # 工具发现
        tools = client.list_tools()
        names = [t["name"] for t in tools]
        assert "prepare_ticket_draft" in names

        # stdio 调用工具
        draft_res = client.call_tool("prepare_ticket_draft", {
            "title": "工位网口掉线",
            "description": "频繁断开连接",
            "category": "C_NET",
        })
        assert "工单草稿已就绪" in draft_res
        assert "工位网口掉线" in draft_res

        # stdio 读取资源
        cat_json = client.read_resource("it://categories/tree")
        assert "C_NET" in cat_json
    finally:
        client.close()
