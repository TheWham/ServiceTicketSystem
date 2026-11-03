# -*- coding: utf-8 -*-
"""MCP Service CLI 启动入口 (支持以 python -m mcp_service 运行 stdio 传输)."""
from .server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
