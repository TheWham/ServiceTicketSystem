# -*- coding: utf-8 -*-
"""生成模型客户端（OpenAI 兼容），并如实交代 token 从哪来。

双模自适应：
- 配了 `AGENT_LLM_BASE_URL` / `AGENT_LLM_API_KEY` → 真调模型，token 取服务端回传的
  `usage`，来源标记 `reported`；
- 没配或调用失败 → 工作流走确定性兜底（规则分类 + 模板文案），token 由本地估算，
  来源标记 `estimated`。

两种情况的区别会在链路大盘和 web 页面上明确标出——把估算值当真实值是 Day17
原脚本的一个坑，这里不重蹈。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from . import config as cfg
from .tracer import TOKENS_ESTIMATED, TOKENS_REPORTED


class ModelUnavailable(RuntimeError):
    """模型未配置或调用失败；由调用方决定是否降级。"""


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中日韩字符约 0.9 token/字，其余按 4 字符/token。

    只用于「没有真模型」时的兜底展示，误差 ±20% 是正常的——所以它在链路上会被
    标记为 `estimated`，不会和真实 usage 混为一谈。
    """
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    other = max(0, len(text) - cjk)
    return max(1, int(cjk * 0.9 + other / 4) + 1)


def _configured_temperature() -> Optional[float]:
    """显式配置的采样温度；未配置返回 None（不往请求里塞该参数）。"""
    raw = (cfg.TEMPERATURE or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


class ModelReply:
    __slots__ = ("content", "tokens_in", "tokens_out", "tokens_source", "finish_reason")

    def __init__(self, content: str, tokens_in: int, tokens_out: int, tokens_source: str,
                 finish_reason: str):
        self.content = content
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.tokens_source = tokens_source
        # "stop"=正常结束；"length"=撞上 max_tokens 被截断。
        # 截断必须能被上游看见：推理模型的思维链会先吃掉额度，正文被拦腰砍断后
        # JSON 不再可解析 —— 不区分「正常但没正文」和「被砍断」，就没法正确降级。
        self.finish_reason = finish_reason


class ModelClient:
    """轻量 OpenAI 兼容客户端：只走 `chat/completions`，只用 httpx，不引额外 SDK。

    整条链路上只有两处会用到它 —— Node 1 的意图分类、Node 3 的终审文案。
    两处都用 `available` 做前置判断，不可用就各自降级（规则路由 / 模板文案），
    因此**没有模型时整条链路仍然跑得通**，只是 token 会被标成 estimated。
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url if base_url is not None else cfg.LLM_BASE_URL).rstrip("/")
        self.api_key = api_key if api_key is not None else cfg.LLM_API_KEY
        self.model = model or cfg.LLM_MODEL
        self.timeout = timeout or cfg.LLM_TIMEOUT

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    def complete(self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None,
                 trace_id: Optional[str] = None) -> ModelReply:
        """一次无工具对话；token 一律取服务端 usage。

        `temperature` 默认不传：部分模型（如 kimi-k3）不接受该参数，传了会直接报错。
        要固定随机性时用 `WORKFLOW_DEMO_TEMPERATURE` / `AGENT_TEMPERATURE` 显式开启。
        `trace_id` 作为 X-Request-Id 随请求外发 —— Day17 要求的「跨服务上下文传递」：
        上游日志带同一个 ID，链路才能跨进程串起来。
        """
        if not self.available:
            raise ModelUnavailable("未配置 AGENT_LLM_* / LLM_* 或 .env 中的 base_url 与 api_key")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or cfg.MAX_OUTPUT_TOKENS,
        }
        temp = temperature if temperature is not None else _configured_temperature()
        if temp is not None:
            payload["temperature"] = temp
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        if trace_id:
            headers["X-Request-Id"] = trace_id
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                body = resp.json()
        except Exception as e:  # noqa: BLE001 —— 网络/协议异常统一转 ModelUnavailable
            raise ModelUnavailable(f"模型调用失败: {type(e).__name__}: {e}") from e

        try:
            choice = body["choices"][0]
            content = choice["message"]["content"] or ""
            # 网关不回该字段时留空 —— 空值按「未知」处理，不当成正常结束。
            finish_reason = str(choice.get("finish_reason") or "")
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            raise ModelUnavailable(f"模型响应结构异常: {e}") from e

        usage = body.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens") or 0)
        tokens_out = int(usage.get("completion_tokens") or 0)
        if tokens_in == 0 and tokens_out == 0:
            # 有些兼容网关不回 usage —— 只能估算，并如实降级标记。
            # 这一支是「调了模型但拿不到 usage」，与「压根没调模型」不同，
            # 所以仍然构造 ModelReply 正常返回，只把来源降级为 estimated。
            prompt_text = "".join(m.get("content") or "" for m in messages)
            return ModelReply(content, estimate_tokens(prompt_text),
                              estimate_tokens(content), TOKENS_ESTIMATED, finish_reason)
        return ModelReply(content, tokens_in, tokens_out, TOKENS_REPORTED, finish_reason)


class NullModelClient(ModelClient):
    """显式禁用模型（用于纯确定性演示：`WORKFLOW_DEMO_NO_MODEL=1`）。"""

    def __init__(self):  # noqa: D107
        super().__init__(base_url="", api_key="")

    @property
    def available(self) -> bool:
        return False