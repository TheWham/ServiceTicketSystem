"""查询改写：把用户口语问题改写为"实际现象 + 规范术语"，供混合检索与精排使用。"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from ..config import load_llm_config

REWRITE_PROMPT = """你是企业 IT 服务台的检索助手。把用户的问题改写成用于检索《IT 故障排查知识库》的查询语句：
1. 只保留用户实际观察到的现象、报错原文、操作场景；删除用户自己对原因的猜测和反问（如"是不是 X 坏了""是不是要加内存"）。
2. 在现象后补充该现象在 IT 运维中的规范术语（例如"撤销对计算机所做的更改"→"Windows 更新安装失败回滚"）。
3. 不得编造用户没有提到的事实；如果问题本身是功能使用/流程咨询而非故障，保持原意，不要改成故障。
4. 只输出改写后的一句查询，不超过 60 个字，不要任何解释。"""


class QueryRewriter:
    """LLM 对话接口做查询改写，带磁盘缓存（按 模型+提示词+原查询 的 sha1）。

    timeout/retries 供在线服务模式收紧预算：默认 30s/2 次（离线评测行为不变），
    服务化时传 1.2s/1 次，超时即回落原查询，不吃光 Java 客户端的总预算。
    """

    def __init__(self, model: str = "", cache_dir: Optional[str] = None,
                 timeout: float = 30.0, retries: int = 2):
        cfg = load_llm_config()
        self.model = model or cfg["clean_model"]
        self.retries = max(1, int(retries))
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.last_ok = False
        self.last_cached = False
        api_key = cfg.get("api_key", "")
        if api_key and not api_key.startswith("sk-replace-") and api_key != "sk-..." and cfg.get("base_url"):
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=timeout)
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
        for _ in range(self.retries):
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
