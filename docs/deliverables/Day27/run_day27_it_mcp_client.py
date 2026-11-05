# -*- coding: utf-8 -*-
"""Day 27 项目端调用客户端演练脚本 (run_day27_it_mcp_client.py).

演示三种企业级调用姿势：
1. 【姿势一：进程内直调 (In-Process)】无进程间管道损耗，适合现有 Python Agent 业务代码快速无缝调用；
2. 【姿势二：OpenAI 格式一键导出】自动将 MCP Tools 规范映射为 OpenAI Function Calling JSON Schema，方便挂载给大模型；
3. 【姿势三：标准 stdio 子进程交互】模拟 Cursor / Claude Desktop / Antigravity 发起真实标准 JSON-RPC 2.0 报文通信。
"""
import json
from pathlib import Path
import sys

# Windows 控制台 UTF-8 输出重整 (防止 gbk 无法编码 emoji)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RAG_PYTHON_ROOT = WORKSPACE_ROOT / "services" / "python-retrieval"
if str(RAG_PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_PYTHON_ROOT))

from mcp_service.client import ITServiceMCPClient

def main():
    print("=" * 80)
    print("🚀 Day 27 项目端 MCP Client 全真调用演练")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 姿势一：进程内高性能直接调用
    # --------------------------------------------------------------------------
    print("\n【姿势一：进程内高性能直接调用 (In-Process Direct Call)】")
    client_inproc = ITServiceMCPClient(mode="in_process")

    # 1. 发现工具
    tools = client_inproc.list_tools()
    print(f"👉 成功发现 {len(tools)} 个标准 MCP 工具：{[t['name'] for t in tools]}")

    # 2. 直调工单草稿整理
    draft_res = client_inproc.call_tool("prepare_ticket_draft", {
        "title": "工位网口亮红灯无法上网",
        "description": "插拔网线无效，IP 获取为 169.254 开头私有地址",
        "category": "C_NET",
        "priority": "HIGH"
    })
    print(f"\n[Tool 结果: 整理工单草稿]\n{draft_res}")

    # 3. 读取只读分类树资源
    cat_tree_raw = client_inproc.read_resource("it://categories/tree")
    cat_tree = json.loads(cat_tree_raw)
    print(f"\n[Resource 结果: 获取分类字典树] 成功拉取 {len(cat_tree['categories'])} 个系统分类")

    # --------------------------------------------------------------------------
    # 姿势二：一键导出为 OpenAI Function Calling 格式
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("【姿势二：动态映射为 OpenAI Tools 格式（供智能体即插即用）】")
    openai_tools = client_inproc.to_openai_tools()
    print(f"👉 成功生成标准 OpenAI Tools 数组（共 {len(openai_tools)} 个）：")
    for t in openai_tools:
        fn = t["function"]
        print(f"   - Tool: {fn['name']:<22} | 描述: {fn['description'][:30]}... | 参数: {list(fn['parameters']['properties'].keys())}")

    # --------------------------------------------------------------------------
    # 姿势三：标准 stdio 子进程跨进程通信 (JSON-RPC 2.0)
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("【姿势三：标准 stdio 跨进程通信 (模拟 Cursor / Claude Desktop / Antigravity)】")
    server_script = str(WORKSPACE_ROOT / "day27" / "run_day27_it_ticket_mcp.py")
    client_stdio = ITServiceMCPClient(mode="stdio", server_cmd=[sys.executable, server_script, "run"])

    try:
        # 发送 tools/call
        print("👉 发起 JSON-RPC 2.0 报文请求: method=tools/call, name=prepare_ticket_draft")
        stdio_draft_res = client_stdio.call_tool("prepare_ticket_draft", {
            "title": "会议室投屏盒子无法连接",
            "description": "HDMI 信号线无画面输入，无线投屏搜索不到设备",
            "category": "C_HW_PR",
            "priority": "MEDIUM"
        })
        print(f"[stdio 管道返回结果]:\n{stdio_draft_res}")

        # 发送 resources/read
        print("\n👉 发起 JSON-RPC 2.0 报文请求: method=resources/read, uri=it://system/status")
        stdio_status_res = client_stdio.read_resource("it://system/status")
        print(f"[stdio 管道返回结果]:\n{stdio_status_res}")
    finally:
        client_stdio.close()

    print("\n" + "=" * 80)
    print("🎉 项目端 MCP Client 三种姿势全链路联调成功！随时可在业务层与 IDE 宿主无缝集成。")
    print("=" * 80)

if __name__ == "__main__":
    main()
