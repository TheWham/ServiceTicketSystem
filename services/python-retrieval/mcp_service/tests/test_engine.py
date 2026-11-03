# -*- coding: utf-8 -*-
import pytest
from mcp_service.engine import ZeroDepFastMCP, FastMCP

def test_engine_tool_registration_and_list():
    mcp = ZeroDepFastMCP("TestServer")

    @mcp.tool()
    def greet(name: str) -> str:
        """Say hello to someone."""
        return f"Hello, {name}!"

    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    resp = mcp.handle_jsonrpc(req)
    assert resp["id"] == 1
    assert "result" in resp
    tools = resp["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "greet"
    assert tools[0]["description"] == "Say hello to someone."
    assert "name" in tools[0]["inputSchema"]["properties"]

def test_engine_tool_call():
    mcp = ZeroDepFastMCP("TestServer")

    @mcp.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 3, "b": 7}},
    }
    resp = mcp.handle_jsonrpc(req)
    assert resp["id"] == 2
    assert resp["result"]["isError"] is False
    assert resp["result"]["content"][0]["text"] == "10"

def test_engine_resource_read():
    mcp = ZeroDepFastMCP("TestServer")

    @mcp.resource("test://info")
    def get_info() -> str:
        return "system_ok"

    req = {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "test://info"}}
    resp = mcp.handle_jsonrpc(req)
    assert resp["result"]["contents"][0]["text"] == "system_ok"

def test_engine_prompt_get():
    mcp = ZeroDepFastMCP("TestServer")

    @mcp.prompt()
    def review_prompt(code: str) -> str:
        """Review code."""
        return f"Please review this code:\n{code}"

    req = {"jsonrpc": "2.0", "id": 4, "method": "prompts/get", "params": {"name": "review_prompt", "arguments": {"code": "print(1)"}}}
    resp = mcp.handle_jsonrpc(req)
    assert resp["id"] == 4
    assert "messages" in resp["result"]
    assert "print(1)" in resp["result"]["messages"][0]["content"]["text"]

def test_engine_initialize():
    mcp = ZeroDepFastMCP("TestServer")
    req = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "testClient", "version": "1.0.0"},
        },
    }
    resp = mcp.handle_jsonrpc(req)
    assert resp["id"] == 0
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert "tools" in resp["result"]["capabilities"]
    assert "resources" in resp["result"]["capabilities"]
    assert "prompts" in resp["result"]["capabilities"]
