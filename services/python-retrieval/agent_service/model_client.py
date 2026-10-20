# -*- coding: utf-8 -*-
"""OpenAI 兼容模型客户端（原生 tools 协议）。

`complete_with_tools` 发送工具定义，允许模型返回 `tool_calls` 或最终文本；
不设 `response_format`（那会禁止 tool_calls）。kimi-k3 不接受 temperature，
默认不传该参数（可用 AGENT_TEMPERATURE 显式覆盖）。
"""

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from . import config as acfg


class ModelError(RuntimeError):
    """模型调用失败（未配置 / 网络 / 协议异常）。"""


class ToolCall:
    __slots__ = ("id", "name", "arguments")

    def __init__(self, call_id: str, name: str, arguments: Dict[str, Any]):
        self.id = call_id
        self.name = name
        self.arguments = arguments


class ModelTurn:
    """一轮模型输出：若干工具调用 或 最终文本（二选一）。"""

    __slots__ = ("tool_calls", "content", "raw_message")

    def __init__(self, tool_calls: List[ToolCall], content: Optional[str], raw_message: Any):
        self.tool_calls = tool_calls
        self.content = content
        self.raw_message = raw_message

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class ModelClient:
    """企业级生成客户端：单例复用，供 ReAct 循环逐轮调用。"""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: Optional[str] = None, timeout: Optional[float] = None):
        if not acfg.model_configured():
            raise ModelError("NOT_CONFIGURED: 未配置 AGENT_LLM_BASE_URL / AGENT_LLM_API_KEY")
        self.client = OpenAI(api_key=api_key or acfg.LLM_API_KEY,
                             base_url=base_url or acfg.LLM_BASE_URL,
                             timeout=timeout or acfg.LLM_TIMEOUT)
        self.model = model or acfg.LLM_MODEL
        self.max_tokens = acfg.MAX_OUTPUT_TOKENS

    def complete_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                            tool_choice: str = "auto") -> ModelTurn:
        kwargs: Dict[str, Any] = dict(model=self.model, messages=messages, tools=tools,
                                      tool_choice=tool_choice, max_tokens=self.max_tokens)
        if acfg.TEMPERATURE:
            try:
                kwargs["temperature"] = float(acfg.TEMPERATURE)
            except ValueError:
                pass
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception as e:  # noqa: BLE001 —— 网络/网关异常统一转 ModelError
            raise ModelError(f"模型调用失败: {type(e).__name__}: {e}") from e
        if not resp.choices:
            raise ModelError("模型未返回 choices")
        msg = resp.choices[0].message
        calls: List[ToolCall] = []
        for tool_call in (msg.tool_calls or []):
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except Exception:  # noqa: BLE001 —— 非法参数按空对象处理，交由工具层报错
                args = {}
            if not isinstance(args, dict):
                args = {}
            calls.append(ToolCall(tool_call.id, tool_call.function.name, args))
        return ModelTurn(calls, msg.content, msg)