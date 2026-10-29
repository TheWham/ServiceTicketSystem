# -*- coding: utf-8 -*-
"""归因叙事模型客户端（OpenAI 兼容），并如实交代 token 从哪来。

整条分析链路只有两处调用模型：意图分类（Node A）与归因叙事（Node D）。
两处都用 `available` 前置判断，不可用就各自降级（规则路由 / 确定性模板），
因此**没有模型时链路仍然跑得通**，只是 token 会被标成 `estimated`。

token 来源在 trace 与页面上分开显示，不合并统计：

  reported  调了模型，取服务端 usage
  estimated 没调模型，或调了但网关不回 usage —— 本地估算
  none      本次没有模型参与（如意图路由被 skip_model 跳过）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from . import config as cfg

TOKENS_REPORTED = "reported"
TOKENS_ESTIMATED = "estimated"
TOKENS_NONE = "none"


class ModelUnavailable(RuntimeError):
    """模型未配置或调用失败；由调用方决定是否降级。"""


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中日韩字符约 0.9 token/字，其余按 4 字符/token。

    只用于「没有真模型」时的兜底展示，误差 ±20% 是正常的 —— 所以它在链路上会被
    标记为 `estimated`，不会和真实 usage 混为一谈。
    """
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    other = max(0, len(text) - cjk)
    return max(1, int(cjk * 0.9 + other / 4) + 1)


def _configured_temperature() -> Optional[float]:
    raw = (cfg.TEMPERATURE or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


class ModelReply:
    """一次模型调用的结果，以及 token 到底是从哪来的。

    `finish_reason` 必须原样带出来：调用方要靠它区分「正常结束但没有正文」与
    「被 max_tokens 砍断」。前者多半是提示词或模型选择问题，后者要调预算或换
    模型 —— 处置完全不同，合成一句"没拿到正文"就只能靠猜。

    `tokens_source` 同理：`reported` 是服务端 usage，`estimated` 是本地估算
    （误差 ±20%），两者不合并统计。
    """

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
    """轻量 OpenAI 兼容客户端：只走 `chat/completions`，只用 httpx。

    刻意不传 `response_format` —— 本仓库的纪律是手写 JSON 校验（见 contract.py
    `parse_narrative`）：`response_format` 不可用时会被 adapter 省略，把
    "结构正确"寄望于它，等于把链路正确性押在一个可以静默缺失的能力上。
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
                 timeout: Optional[float] = None,
                 trace_id: Optional[str] = None) -> ModelReply:
        """一次无工具对话；token 一律取服务端 usage，拿不到则如实标 estimated。

        `timeout` 可逐次覆盖（默认用构造时的 `self.timeout`）：链路上两处调用的
        合理等待时间差一个量级 —— Node A 的路由/抽槽是短任务，卡住就该立刻退回
        规则；Node D 的归因叙事要给推理模型几十秒。共用一个超时会让短的迁就长的。
        """
        if not self.available:
            raise ModelUnavailable(
                "未配置 ANALYTICS_LLM_* / LLM_* 或 .env 中的 base_url 与 api_key")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or cfg.SYNTH_MAX_OUTPUT_TOKENS,
        }
        temp = temperature if temperature is not None else _configured_temperature()
        if temp is not None:
            payload["temperature"] = temp
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": "application/json"}
        if trace_id:
            headers["X-Request-Id"] = trace_id
        try:
            with httpx.Client(timeout=timeout or self.timeout) as client:
                resp = client.post(f"{self.base_url}/chat/completions",
                                   json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
        except Exception as e:  # noqa: BLE001 —— 网络/协议异常统一转 ModelUnavailable
            raise ModelUnavailable(f"模型调用失败: {type(e).__name__}: {e}") from e

        try:
            choice = body["choices"][0]
            content = choice["message"]["content"] or ""
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
    """显式禁用模型（用于纯确定性演示：`ANALYTICS_NO_MODEL=1`）。"""

    def __init__(self):  # noqa: D107
        super().__init__(base_url="", api_key="")

    @property
    def available(self) -> bool:
        return False