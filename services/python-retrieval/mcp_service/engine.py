# -*- coding: utf-8 -*-
"""双模自适应 FastMCP 引擎 (Zero-Dependency Fallback Engine).

当环境中未安装官方 `mcp` 库时，提供 100% 契约等价的标准 JSON-RPC 2.0 stdio 协议引擎。
支持方法：
- initialize / notifications/initialized / ping
- tools/list / tools/call
- resources/list / resources/read
- prompts/list / prompts/get
"""
import inspect
import json
import logging
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints

log = logging.getLogger(__name__)

# 类型映射表：Python 类型 -> JSON Schema 类型
_TYPE_MAPPING = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _python_type_to_schema(py_type: Any) -> Dict[str, Any]:
    """将 Python 参数类型注解转换为 JSON Schema 描述。"""
    # 处理 Optional[T] 或 Union[T, None]
    origin = getattr(py_type, "__origin__", None)
    args = getattr(py_type, "__args__", ())

    if origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _python_type_to_schema(non_none_args[0])

    if py_type in _TYPE_MAPPING:
        return {"type": _TYPE_MAPPING[py_type]}

    # 兜底字符串
    return {"type": "string"}


def _build_input_schema(func: Callable) -> Dict[str, Any]:
    """通过函数签名自动推导 MCP 工具的 inputSchema。"""
    sig = inspect.signature(func)
    try:
        type_hints = get_type_hints(func)
    except Exception:
        type_hints = {}

    properties: Dict[str, Any] = {}
    required: List[str] = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue

        p_type = type_hints.get(name, str)
        schema = _python_type_to_schema(p_type)

        # 提取 Docstring 中的参数描述（若有）
        doc = inspect.getdoc(func) or ""
        desc = ""
        for line in doc.splitlines():
            line_s = line.strip()
            if line_s.startswith(f":param {name}:"):
                desc = line_s.split(f":param {name}:", 1)[1].strip()
                break
        if desc:
            schema["description"] = desc

        properties[name] = schema

        # 检查是否为必需参数（无默认值）
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


class ZeroDepFastMCP:
    """零外部依赖的生产级 FastMCP 仿真与协议引擎。"""

    def __init__(self, name: str = "FastMCPServer"):
        self.name = name
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.resources: Dict[str, Dict[str, Any]] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}

    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        """发布标准 MCP Tool 装饰器。"""
        def decorator(func: Callable):
            t_name = name or func.__name__
            t_desc = description or inspect.getdoc(func) or f"Execute {t_name}"
            # 首行作为简明描述
            t_short_desc = t_desc.splitlines()[0].strip() if t_desc else t_name
            input_schema = _build_input_schema(func)

            self.tools[t_name] = {
                "name": t_name,
                "description": t_short_desc,
                "func": func,
                "inputSchema": input_schema,
            }
            return func
        return decorator

    def resource(self, uri: str, name: Optional[str] = None, description: Optional[str] = None):
        """发布标准 MCP Resource 装饰器。"""
        def decorator(func: Callable):
            r_name = name or func.__name__
            r_desc = description or inspect.getdoc(func) or f"Read {uri}"
            self.resources[uri] = {
                "uri": uri,
                "name": r_name,
                "description": r_desc,
                "func": func,
            }
            return func
        return decorator

    def prompt(self, name: Optional[str] = None, description: Optional[str] = None):
        """发布标准 MCP Prompt 模版装饰器。"""
        def decorator(func: Callable):
            p_name = name or func.__name__
            p_desc = description or inspect.getdoc(func) or f"Prompt template {p_name}"
            self.prompts[p_name] = {
                "name": p_name,
                "description": p_desc,
                "func": func,
            }
            return func
        return decorator

    def handle_jsonrpc(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单条 JSON-RPC 2.0 请求报文并返回响应（通知请求无响应返回 None）。"""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        # 1. 协议握手初始化
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": "1.0.0",
                    },
                },
            }

        if method == "notifications/initialized":
            return None

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        # 2. Tools 原语
        if method == "tools/list":
            tools_list = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["inputSchema"],
                }
                for t in self.tools.values()
            ]
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}

        if method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments") or {}

            if tool_name not in self.tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: Unknown tool '{tool_name}'",
                    },
                }

            tool_entry = self.tools[tool_name]
            try:
                res = tool_entry["func"](**args)
                text_out = res if isinstance(res, str) else json.dumps(res, ensure_ascii=False)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": str(text_out)}],
                        "isError": False,
                    },
                }
            except Exception as e:
                log.exception("Tool execution error in %s", tool_name)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"❌ 工具执行异常: {type(e).__name__}: {e}"}],
                        "isError": True,
                    },
                }

        # 3. Resources 原语
        if method == "resources/list":
            res_list = [
                {
                    "uri": r["uri"],
                    "name": r["name"],
                    "description": r["description"],
                    "mimeType": "application/json",
                }
                for r in self.resources.values()
            ]
            return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": res_list}}

        if method == "resources/read":
            uri = params.get("uri")
            if uri not in self.resources:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": f"Invalid params: Resource URI '{uri}' not found",
                    },
                }
            res_entry = self.resources[uri]
            try:
                text_content = res_entry["func"]()
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": str(text_content),
                            }
                        ]
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": f"Resource read error: {e}"},
                }

        # 4. Prompts 原语
        if method == "prompts/list":
            p_list = [
                {
                    "name": p["name"],
                    "description": p["description"],
                }
                for p in self.prompts.values()
            ]
            return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": p_list}}

        if method == "prompts/get":
            p_name = params.get("name")
            p_args = params.get("arguments") or {}
            if p_name not in self.prompts:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Prompt not found: '{p_name}'",
                    },
                }
            p_entry = self.prompts[p_name]
            try:
                rendered = p_entry["func"](**p_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "description": p_entry["description"],
                        "messages": [
                            {
                                "role": "user",
                                "content": {"type": "text", "text": str(rendered)},
                            }
                        ],
                    },
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": f"Prompt render error: {e}"},
                }

        # 未知方法
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not supported: '{method}'"},
        }

    def run(self, transport: str = "stdio"):
        """以标准 stdio 运行监听，逐行处理 JSON-RPC 报文。"""
        if transport != "stdio":
            raise NotImplementedError(f"Transport '{transport}' not implemented in zero-dependency engine.")

        # 确保标准输出与标准输入以 UTF-8 处理 (防止 Windows 平台默认 GBK 编解码乱码)
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                req = json.loads(line_str)
                resp = self.handle_jsonrpc(req)
                if resp is not None:
                    out = json.dumps(resp, ensure_ascii=False)
                    sys.stdout.write(out + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                }
                sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()


# 双模自适应导出
try:
    from mcp.server.fastmcp import FastMCP as NativeFastMCP
    MCP_NATIVE_AVAILABLE = True
    FastMCP = NativeFastMCP
except ImportError:
    MCP_NATIVE_AVAILABLE = False
    FastMCP = ZeroDepFastMCP
