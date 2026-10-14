"""查询改写：把用户口语问题改写为"实际现象 + 规范术语"，供混合检索与精排使用。

为什么需要（Day13 开发集实测）：
  - 用户常把自己对原因的猜测写进问题（"是不是开不了机了""是不是带宽被占了"），
    Cross-Encoder 会顺着猜测把兄弟卡打高分，正确卡反被压到第 2；
  - 用户的口语描述与卡片术语错位（"撤销对计算机所做的更改" vs 卡片写的"回滚"），
    Dense/BM25 前 15 个候选里根本没有目标卡，精排无从救起。
改写只做两件事：删掉猜测、补上规范术语。原查询仍参与召回（多查询 RRF），
改写失败时回落原查询，检索链路不因 LLM 故障中断。
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from ..embedding import load_ksp_config, _parse_env_file, PROJECT_ROOT

REWRITE_PROMPT = """你是企业 IT 服务台的检索助手。把用户的问题改写成用于检索《IT 故障排查知识库》的查询语句：
1. 只保留用户实际观察到的现象、报错原文、操作场景；删除用户自己对原因的猜测和反问（如"是不是 X 坏了""是不是要加内存"）。
2. 在现象后补充该现象在 IT 运维中的规范术语（例如"撤销对计算机所做的更改"→"Windows 更新安装失败回滚"）。
3. 不得编造用户没有提到的事实；如果问题本身是功能使用/流程咨询而非故障，保持原意，不要改成故障。
4. 只输出改写后的一句查询，不超过 60 个字，不要任何解释。"""


class QueryRewriter:
    """KSP OpenAI 兼容 Chat 接口做查询改写，带磁盘缓存（按 模型+提示词+原查询 的 sha1）。"""

    def __init__(self, model: str = "", cache_dir: Optional[str] = None):
        cfg = load_ksp_config()
        env = _parse_env_file(PROJECT_ROOT / ".env")
        # 默认用清洗模型（deepseek-v4-flash，快）；kimi-k3 等推理模型改写延迟过高
        self.model = model or env.get("KSP_CLEAN_MODEL") or "deepseek-v4-flash"
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.last_ok = False
        self.last_cached = False
        if cfg["api_key"] and cfg["base_url"]:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"], timeout=30)
            except ImportError:
                print("       ⚠️ 未安装 openai 包，查询改写不可用，回落原查询")

    def _cache_file(self, query: str) -> Optional[Path]:
        if not self.cache_dir:
            return None
        key = hashlib.sha1(f"{self.model}\n{REWRITE_PROMPT}\n{query}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def rewrite(self, query: str) -> str:
        """返回改写后的查询；任何失败都回落原查询，并把 last_ok 置 False 供调用方记录。"""
        cache = self._cache_file(query)
        self.last_cached = bool(cache and cache.exists())
        if self.last_cached:
            self.last_ok = True
            return json.loads(cache.read_text(encoding="utf-8"))["rewrite"]
        if self.client is None:
            self.last_ok = False
            return query
        for _ in range(2):  # 偶发空响应：重试一次
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": REWRITE_PROMPT},
                              {"role": "user", "content": query}],
                )
                text = (resp.choices[0].message.content or "").strip()
            except Exception as e:
                print(f"       ⚠️ 查询改写失败，回落原查询：{e}")
                break
            if text:
                rewritten = text.splitlines()[0].strip()
                if cache:
                    cache.write_text(json.dumps({"query": query, "rewrite": rewritten, "model": self.model},
                                                ensure_ascii=False), encoding="utf-8")
                self.last_ok = True
                return rewritten
        self.last_ok = False
        return query
