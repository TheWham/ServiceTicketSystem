# -*- coding: utf-8 -*-
"""项目端通用 MCP 客户端适配器 (ITServiceMCPClient).

支持两种运行模式：
1. mode="in_process": 进程内零开销直调，适合 Agent 业务或项目内服务直接无缝引用；
2. mode="stdio": 启动标准子进程，通过标准管道读写 JSON-RPC 2.0 报文，适合协议验证。
提供 to_openai_tools() 便捷方法将 MCP 工具定义导出为 OpenAI Function Calling 格式。
"""
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .server import mcp as local_mcp

log = logging.getLogger(__name__)


class ITServiceMCPClient:
    """通用企业 IT 服务 MCP 客户端。"""

    def __init__(
        self,
        mode: str = "in_process",
        server_cmd: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        self.mode = mode.lower()
        self.server_cmd = server_cmd
        self._proc: Optional[subprocess.Popen] = None
        self._req_id = 0

        if self.mode == "stdio":
            self._init_stdio_process(env)

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _init_stdio_process(self, env: Optional[Dict[str, str]] = None):
        """初始化 stdio 子进程并完成 initialize 握手。"""
        # 构建启动命令
        if not self.server_cmd:
            cmd = [sys.executable, "-m", "mcp_service"]
        else:
            cmd = self.server_cmd

        # 继承当前系统环境并追加 PYTHONPATH
        sub_env = os.environ.copy()
        pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        sub_env["PYTHONPATH"] = pkg_root + os.pathsep + sub_env.get("PYTHONPATH", "")
        sub_env["PYTHONIOENCODING"] = "utf-8"
        sub_env["PYTHONUTF8"] = "1"
        if env:
            sub_env.update(env)

        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=sub_env,
        )

        # 发送 initialize 请求
        init_req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ITServiceMCPClient", "version": "1.0.0"},
            },
        }
        resp = self._send_stdio_json(init_req)
        if not resp or "result" not in resp:
            raise RuntimeError(f"MCP stdio server handshake failed: {resp}")

    def _send_stdio_json(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """向 stdio 进程发送 JSON 报文并同步读取单行返回。"""
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            raise RuntimeError("stdio process is not alive.")

        payload = json.dumps(req, ensure_ascii=False) + "\n"
        self._proc.stdin.write(payload)
        self._proc.stdin.flush()

        line = self._proc.stdout.readline()
        if not line:
            stderr_out = self._proc.stderr.read() if self._proc.stderr else ""
            raise RuntimeError(f"stdio process terminated unexpectedly. Stderr: {stderr_out}")

        return json.loads(line.strip())

    def list_tools(self) -> List[Dict[str, Any]]:
        """发现所有可用 Tools。"""
        req = {"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/list", "params": {}}
        if self.mode == "in_process":
            resp = local_mcp.handle_jsonrpc(req)
        else:
            resp = self._send_stdio_json(req)

        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """调用指定工具并返回纯文本结果。"""
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        if self.mode == "in_process":
            resp = local_mcp.handle_jsonrpc(req)
        else:
            resp = self._send_stdio_json(req)

        if "error" in resp:
            return f"❌ RPC 错误: {resp['error'].get('message')}"

        content_list = resp.get("result", {}).get("content", [])
        if content_list and isinstance(content_list, list):
            return content_list[0].get("text", "")
        return json.dumps(resp.get("result", {}), ensure_ascii=False)

    def read_resource(self, uri: str) -> str:
        """读取指定 URI 的 Resource 只读内容。"""
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "resources/read",
            "params": {"uri": uri},
        }
        if self.mode == "in_process":
            resp = local_mcp.handle_jsonrpc(req)
        else:
            resp = self._send_stdio_json(req)

        if "error" in resp:
            return f"❌ Resource 读取错误: {resp['error'].get('message')}"

        contents = resp.get("result", {}).get("contents", [])
        if contents and isinstance(contents, list):
            return contents[0].get("text", "")
        return ""

    def get_prompt(self, name: str, arguments: Dict[str, Any]) -> str:
        """获取并渲染指定名称的 Prompt 模版。"""
        req = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "prompts/get",
            "params": {"name": name, "arguments": arguments},
        }
        if self.mode == "in_process":
            resp = local_mcp.handle_jsonrpc(req)
        else:
            resp = self._send_stdio_json(req)

        if "error" in resp:
            return f"❌ Prompt 获取错误: {resp['error'].get('message')}"

        messages = resp.get("result", {}).get("messages", [])
        if messages and isinstance(messages, list):
            return messages[0].get("content", {}).get("text", "")
        return ""

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        """将 MCP Tools 动态转换为标准 OpenAI Function Calling 规范结构。"""
        tools = self.list_tools()
        openai_tools: List[Dict[str, Any]] = []

        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                },
            })
        return openai_tools

    def close(self):
        """释放 stdio 子进程资源。"""
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2)
            except Exception:
                self._proc.kill()
            finally:
                self._proc = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
