# -*- coding: utf-8 -*-
"""OpenAI 兼容模型客户端（原生 tools 协议）。

`complete_with_tools` 发送工具定义，允许模型返回 `tool_calls` 或最终文本；
不设 `response_format`（那会禁止 tool_calls）。kimi-k3 不接受 temperature，
默认不传该参数（可用 AGENT_TEMPERATURE 显式覆盖）。
"""
import json
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ModelUsage:
    """模型返回的真实 token 用量；缺失时必须保持 0，不做估算。"""
    tokens_in: int = 0
    tokens_out: int = 0
    total_tokens: int = 0
    reported: bool = False

    @property
    def tokens_source(self) -> str:
        return "reported" if self.reported else "none"


class ModelTurn:
    """一轮模型输出：若干工具调用 或 最终文本（二选一）。"""

    __slots__ = ("tool_calls", "content", "raw_message", "usage")

    def __init__(self, tool_calls: List[ToolCall], content: Optional[str], raw_message: Any,
                 usage: Optional[ModelUsage] = None):
        self.tool_calls = tool_calls
        self.content = content
        self.raw_message = raw_message
        self.usage = usage or ModelUsage()

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


def _usage_from_response(resp: Any) -> ModelUsage:
    usage = getattr(resp, "usage", None)
    if usage is None:
        return ModelUsage()
    def _num(name: str) -> int:
        value = getattr(usage, name, None)
        if value is None:
            value = usage.get(name) if hasattr(usage, "get") else None
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
    tokens_in = _num("prompt_tokens") or _num("input_tokens")
    tokens_out = _num("completion_tokens") or _num("output_tokens")
    total = _num("total_tokens") or tokens_in + tokens_out
    return ModelUsage(tokens_in=tokens_in, tokens_out=tokens_out, total_tokens=total,
                      reported=bool(tokens_in or tokens_out))


class StreamingAnswerExtractor:
    """从流式 JSON 响应中实时提取 answerText 字段的增量内容。"""
    def __init__(self):
        self.buffer = ""
        self.state = "SEEKING"  # SEEKING, STREAMING, ENDED, RAW
        self.escaped = False
        self.hex_buffer = []

    def push(self, chunk: str) -> str:
        deltas = []
        for char in chunk:
            if self.state == "SEEKING":
                self.buffer += char
                stripped = self.buffer.strip()
                if stripped and not stripped.startswith("{"):
                    self.state = "RAW"
                    deltas.append(self.buffer)
                    self.buffer = ""
                    continue

                idx = self.buffer.find('"answerText"')
                if idx != -1:
                    colon_idx = self.buffer.find(":", idx)
                    if colon_idx != -1:
                        quote_idx = self.buffer.find('"', colon_idx)
                        if quote_idx != -1:
                            self.state = "STREAMING"
                            self.buffer = ""
                elif len(self.buffer) > 120 and not stripped.startswith("{"):
                    self.state = "RAW"
                    deltas.append(self.buffer)
                    self.buffer = ""
            elif self.state == "STREAMING":
                if self.hex_buffer:
                    self.hex_buffer.append(char)
                    if len(self.hex_buffer) == 4:
                        try:
                            deltas.append(chr(int("".join(self.hex_buffer), 16)))
                        except Exception:
                            pass
                        self.hex_buffer = []
                elif self.escaped:
                    self.escaped = False
                    if char == "u":
                        self.hex_buffer = []
                    elif char == "n":
                        deltas.append("\n")
                    elif char == "t":
                        deltas.append("\t")
                    elif char == "r":
                        deltas.append("\r")
                    elif char == '"':
                        deltas.append('"')
                    elif char == "\\":
                        deltas.append("\\")
                    else:
                        deltas.append(char)
                else:
                    if char == "\\":
                        self.escaped = True
                    elif char == '"':
                        self.state = "ENDED"
                    else:
                        deltas.append(char)
            elif self.state == "RAW":
                deltas.append(char)
        return "".join(deltas)


class ModelClient:
    """企业级生成客户端：单例复用，供 ReAct 循环逐轮调用。"""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: Optional[str] = None, timeout: Optional[float] = None,
                 stream_callback: Optional[Any] = None):
        if not acfg.model_configured():
            raise ModelError("NOT_CONFIGURED: 未配置 AGENT_LLM_BASE_URL / AGENT_LLM_API_KEY")
        self.client = OpenAI(api_key=api_key or acfg.LLM_API_KEY,
                             base_url=base_url or acfg.LLM_BASE_URL,
                             timeout=timeout or acfg.LLM_TIMEOUT)
        self.model = model or acfg.LLM_MODEL
        self.max_tokens = acfg.MAX_OUTPUT_TOKENS
        self.stream_callback = stream_callback

    def clone_with_model(self, model_name: str, stream_callback: Optional[Any] = None) -> "ModelClient":
        """派生指定模型的客户端（共享底层 HTTP 连接池与凭据，线程安全隔离）。"""
        if self.__class__ is not ModelClient:
            self.model = model_name
            if stream_callback is not None:
                self.stream_callback = stream_callback
            return self
        cloned = ModelClient.__new__(ModelClient)
        cloned.client = getattr(self, "client", None)
        cloned.model = model_name
        cloned.max_tokens = getattr(self, "max_tokens", acfg.MAX_OUTPUT_TOKENS)
        cloned.stream_callback = stream_callback if stream_callback is not None else getattr(self, "stream_callback", None)
        return cloned

    def complete_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                            tool_choice: str = "auto", model_override: Optional[str] = None,
                            stream_deltas: bool = True) -> ModelTurn:
        target_model = model_override or self.model
        if self.stream_callback is not None:
            extractor = StreamingAnswerExtractor()
            last_turn = None
            for event_type, data in self.complete_with_tools_stream(messages, tools, tool_choice=tool_choice, model_override=target_model):
                if event_type == "reasoning":
                    try:
                        self.stream_callback("reasoning", data)
                    except Exception:
                        pass
                elif event_type == "delta" and stream_deltas:
                    extracted = extractor.push(data)
                    if extracted:
                        try:
                            self.stream_callback("delta", extracted)
                        except Exception:
                            pass
                elif event_type == "turn":
                    last_turn = data
            if last_turn is not None:
                return last_turn

        kwargs: Dict[str, Any] = dict(model=target_model, messages=messages, tools=tools,
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
        return ModelTurn(calls, msg.content, msg, _usage_from_response(resp))

    def complete_with_tools_stream(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]],
                                   tool_choice: str = "auto", model_override: Optional[str] = None):
        """流式调用模型：逐 chunk 产出 ("delta", text) 或 ("reasoning", text)，最后产出 ("turn", ModelTurn)。"""
        if self.__class__ is not ModelClient:
            turn = self.complete_with_tools(messages, tools, tool_choice=tool_choice)
            if turn.content:
                yield ("delta", turn.content)
            yield ("turn", turn)
            return

        target_model = model_override or self.model
        kwargs: Dict[str, Any] = dict(model=target_model, messages=messages, tools=tools,
                                      tool_choice=tool_choice, max_tokens=self.max_tokens,
                                      stream=True)
        if acfg.TEMPERATURE:
            try:
                kwargs["temperature"] = float(acfg.TEMPERATURE)
            except ValueError:
                pass

        try:
            kwargs["stream_options"] = {"include_usage": True}
            resp_stream = self.client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("stream_options", None)
            try:
                resp_stream = self.client.chat.completions.create(**kwargs)
            except Exception as e:
                raise ModelError(f"模型流式调用失败: {type(e).__name__}: {e}") from e

        accumulated_content = []
        tool_calls_dict = {}
        final_usage = None

        for chunk in resp_stream:
            if getattr(chunk, "usage", None):
                final_usage = _usage_from_response(chunk)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield ("reasoning", reasoning)
            content = getattr(delta, "content", None)
            if content:
                accumulated_content.append(content)
                yield ("delta", content)
            if getattr(delta, "tool_calls", None):
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_dict:
                        tool_calls_dict[idx] = {
                            "id": tc.id or "",
                            "name": (tc.function.name if tc.function and tc.function.name else ""),
                            "arguments": []
                        }
                    if tc.id:
                        tool_calls_dict[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls_dict[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls_dict[idx]["arguments"].append(tc.function.arguments)

        full_text = "".join(accumulated_content) if accumulated_content else None
        calls: List[ToolCall] = []
        for idx in sorted(tool_calls_dict.keys()):
            item = tool_calls_dict[idx]
            arg_str = "".join(item["arguments"])
            try:
                parsed_args = json.loads(arg_str or "{}")
            except Exception:
                parsed_args = {}
            if not isinstance(parsed_args, dict):
                parsed_args = {}
            calls.append(ToolCall(item["id"], item["name"], parsed_args))

        if final_usage is None or (final_usage.tokens_in == 0 and final_usage.tokens_out == 0):
            from .cost_governance import estimate_tokens
            prompt_str = "".join(str(m.get("content") or "") for m in messages)
            tokens_in = max(1, estimate_tokens(prompt_str) + 150)
            tokens_out = max(1, estimate_tokens(full_text or ""))
            final_usage = ModelUsage(
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                total_tokens=tokens_in + tokens_out,
                reported=False
            )

        turn = ModelTurn(calls, full_text, None, final_usage)
        yield ("turn", turn)

