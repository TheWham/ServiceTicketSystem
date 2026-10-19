# -*- coding: utf-8 -*-
"""GroundingGenerator：把检索命中的父卡片段交给 LLM，生成带溯源角标的答案。

工程要点：
- 调用形态与 rag_pipeline.retrieval.query_rewriter 一致（openai.OpenAI + chat.completions，
  kimi-k3 不传 temperature）；
- 磁盘答案缓存（sha1：模型 + 系统提示词 + 问题 + 上下文指纹）——演示前预热一次，
  断网即可复用真实答案；
- 任何异常 → OfflineError，由服务层决定离线兜底（绝不编造答案）；
- DAY15_OFFLINE=1 时直接判离线（彩排用）。
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

from rag_pipeline.config import load_llm_config

from . import config as dcfg
from .prompts import STRICT_GROUNDING_PROMPT, build_user_message


class OfflineError(RuntimeError):
    """LLM 生成不可用（断网 / 网关异常 / 强制离线）：服务层据此走结构化兜底。"""


def _contexts_fingerprint(contexts: List[Dict[str, str]]) -> str:
    """对 grounding 上下文做 sha1：卡片 id + 内容前缀，用于答案缓存的"命中卡变了就换 key"。"""
    parts = [f"{c.get('card_id', '')}|{c.get('content', '')[:2000]}" for c in contexts]
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()


class GroundingGenerator:
    """受约束生成器：kimi-k3 + STRICT_GROUNDING_PROMPT，带磁盘缓存与离线兜底。

    工程要点：
    - 调用形态与 query_rewriter 一致（openai.OpenAI + chat.completions，kimi-k3 不传 temperature）；
    - 磁盘答案缓存（按 模型+系统提示词+上下文指纹+问题 的 sha1），演示前预热一次断网可复用；
    - 任何异常 → OfflineError，由 service 层决定离线兜底（绝不编造答案）；
    - DAY15_OFFLINE=1 强制离线（彩排用）。
    """

    def __init__(self,
                 cache_dir: Optional[str] = None,
                 timeout: float = dcfg.LLM_TIMEOUT,
                 retries: int = dcfg.LLM_RETRIES):
        """初始化生成器：加载 LLM 配置、建缓存目录、自检是否可用。

        Args:
            cache_dir: 答案缓存目录；默认 DAY15_ANSWER_CACHE_DIR。
            timeout: 单次 LLM 调用超时（秒）。
            retries: 生成重试次数。
        """
        cfg = load_llm_config()
        self.model = cfg["chat_model"]
        self.retries = max(1, int(retries))
        self.cache_dir = Path(cache_dir) if cache_dir else dcfg.ANSWER_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.last_cached = False
        self.offline_forced = dcfg.OFFLINE

        self.client = None
        api_key = cfg.get("api_key", "")
        if (api_key and not api_key.startswith("sk-replace-") and api_key != "sk-..."
                and cfg.get("base_url") and not self.offline_forced):
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=timeout)
            except ImportError:
                print("       ⚠️ 未安装 openai 包，LLM 生成不可用，走离线兜底")

    @property
    def available(self) -> bool:
        return self.client is not None and not self.offline_forced

    def _cache_file(self, question: str, fp: str) -> Path:
        """答案缓存文件路径：sha1(模型 + 系统提示词 + 上下文指纹 + 问题)。

        把系统提示词也纳入 key —— 改一次 prompt 即令旧缓存整体失效，避免"提示词升级了
        但命中旧答案"的静默错配。
        """
        key = hashlib.sha1(
            f"{self.model}\n{STRICT_GROUNDING_PROMPT}\n{fp}\n{question}".encode("utf-8")
        ).hexdigest()
        return self.cache_dir / f"{key}.json"

    def generate(self, question: str, contexts: List[Dict[str, str]]) -> str:
        """生成带溯源角标的答案（三级：缓存 → 在线 LLM → 抛 OfflineError 交由上层兜底）。

        流程：先算上下文指纹查缓存，命中即零 API 成本返回；否则调 kimi-k3 生成并落盘缓存。
        任何网络/网关异常或强制离线都抛 OfflineError —— **绝不在生成失败时编造内容**，
        由 service 层决定"返回检索片段 + 明示离线"的兜底。

        副作用：把本次是否命中缓存写入 self.last_cached（供 service 标记 mode="cache"）。

        Args:
            question: 用户问题原文。
            contexts: grounding 上下文列表（每项含 card_id/title/version/status/source_file/content）。

        Returns:
            LLM 生成的答案正文（含 [来源: 卡片id - 章节名] 角标）。

        Raises:
            OfflineError: 强制离线 / 未配置 LLM / 调用失败重试尽。
        """
        fp = _contexts_fingerprint(contexts)
        cache = self._cache_file(question, fp)
        self.last_cached = cache.exists()
        if self.last_cached:
            try:
                return json.loads(cache.read_text(encoding="utf-8"))["answer"]
            except Exception:
                pass  # 缓存损坏按未命中处理

        if self.offline_forced or self.client is None:
            raise OfflineError("LLM 生成不可用（强制离线或未配置 LLM_API_KEY/LLM_BASE_URL）")

        user_msg = build_user_message(question, contexts)
        last_err: Optional[Exception] = None
        for _ in range(self.retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": STRICT_GROUNDING_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    # kimi-k3 服务端只接受 temperature=1，故不传该参数
                )
                text = (resp.choices[0].message.content or "").strip()
            except Exception as e:  # noqa: BLE001 —— 网络/网关异常统一转离线
                last_err = e
                continue
            if text:
                try:
                    cache.write_text(json.dumps(
                        {"question": question, "answer": text, "model": self.model,
                         "contexts_fp": fp}, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
                return text
        raise OfflineError(f"LLM 生成失败：{last_err}")
