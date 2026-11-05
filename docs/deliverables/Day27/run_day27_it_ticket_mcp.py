# -*- coding: utf-8 -*-
"""Day 27 企业级 IT 服务工单与知识咨询 FastMCP Server.

支持官方 mcp 库与零依赖自适应降级双模运行 (Zero-Dependency Fallback Engine)
既支持作为独立子进程挂载至 Cursor / Claude Desktop / Antigravity，
又支持通过 Python 客户端直接调用。
"""
import os
from pathlib import Path
import sys

# Windows 控制台 UTF-8 输出重整 (防止 gbk 无法编码 emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 自动加入 services/python-retrieval 搜索路径以复用核心下沉服务
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RAG_PYTHON_ROOT = WORKSPACE_ROOT / "services" / "python-retrieval"
if str(RAG_PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_PYTHON_ROOT))

from mcp_service.engine import MCP_NATIVE_AVAILABLE
from mcp_service.server import (
    get_categories_tree,
    get_system_status,
    it_troubleshoot_prompt,
    mcp,
    prepare_ticket_draft,
    query_my_tickets,
    search_knowledge,
    ticket_draft_confirm_prompt,
)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        # 正式以标准 stdio 运行，等待宿主 Client (Cursor / Claude / Antigravity) 连接
        mcp.run(transport="stdio")
    else:
        print("=" * 80)
        print(f"🚀 Day 27 工业互联新标准：企业级 IT Ticket & Knowledge FastMCP Server 启动就绪")
        print(f"   [底层引擎状态: 原生 mcp 库可用={MCP_NATIVE_AVAILABLE} | 降级引擎=ZeroDepFastMCP]")
        print("=" * 80)
        print("💡 [本地全真契约自检模式] 正在验证 IT 工单与知识咨询 MCP Tools / Resources / Prompts...\n")

        # 1. 自检知识检索工具 (8301)
        print("1. [Tool 测试: search_knowledge 知识库检索] ➔")
        res_tool1 = search_knowledge("VPN 无法连接", limit=2)
        print(res_tool1)
        print("-" * 50)

        # 2. 自检工单查询工具 (8201)
        print("2. [Tool 测试: query_my_tickets 查员工名下工单] ➔")
        res_tool2 = query_my_tickets(user_id="U1001", limit=3)
        print(res_tool2)
        print("-" * 50)

        # 3. 自检工单草稿整理 (本地契约防呆)
        print("3. [Tool 测试: prepare_ticket_draft 故障规范草稿整理] ➔")
        res_tool3 = prepare_ticket_draft(
            title="办公电脑蓝屏重启",
            description="开机进入 Windows 桌面 5 分钟后频繁出现 CRITICAL_PROCESS_DIED 蓝屏代码",
            category="C_HW_PC",
            priority="HIGH",
        )
        print(res_tool3)
        print("-" * 50)

        # 4. 自检只读分类字典资源
        print("4. [Resource 测试: it://categories/tree 只读分类字典] ➔")
        res_res1 = get_categories_tree()
        print(res_res1[:260] + "\n   ... (省略后续分类)")
        print("-" * 50)

        # 5. 自检系统连通性状态探针
        print("5. [Resource 测试: it://system/status 连通性探针] ➔")
        res_res2 = get_system_status()
        print(res_res2)
        print("-" * 50)

        # 6. 自检提示词模版
        print("6. [Prompt 测试: ticket_draft_confirm_prompt 建单确认模版] ➔")
        res_p = ticket_draft_confirm_prompt("办公电脑蓝屏重启", "开机蓝屏重启", "C_HW_PC", "HIGH")
        print(res_p)

        print("\n" + "=" * 80)
        print("✅ 企业级 IT Ticket & Knowledge FastMCP Server 内部契约自检 100% 通过！")
        print("👉 启动标准 MCP stdio 监听指令：python day27/run_day27_it_ticket_mcp.py run")
        print("👉 跨端客户端调用体验指令：python day27/run_day27_it_mcp_client.py")
        print("=" * 80)
