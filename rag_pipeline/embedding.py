"""KSP OpenAI 兼容嵌入提供者与配置加载（自索引构建流水线平移）。"""

import os
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Embedding 配置统一走 config.load_embedding_config（独立 EMBED_API_KEY/EMBED_BASE_URL/EMBED_MODEL）
from .config import load_embedding_config


class KspEmbeddingProvider:
    """
    KSP OpenAI 兼容 /embeddings 提供者（默认 qwen3-embedding-8b，4096 维）：
    - 批量请求降低往返开销
    - 磁盘缓存（按 sha1），重跑零 API 成本
    - 接口异常时自动降级 hash 兜底向量，保证流水线不中断
    """

    def __init__(self, cfg: Optional[Dict[str, str]] = None, cache_dir: Optional[str] = None,
                 batch_size: int = 32, model_override: Optional[str] = None):
        self.cfg = cfg or load_embedding_config()
        self.model = model_override or self.cfg["model"]
        self.batch_size = batch_size
        self.available = bool(self.cfg["api_key"] and self.cfg["base_url"])
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        if self.available:
            # 首次自检，失败则降级
            try:
                self._call_api(["embedding 自检"])
                self.engine_type = f"KSP OpenAI兼容 /embeddings ({self.model})"
            except Exception as e:
                self.available = False
                self.engine_type = f"KSP 不可用({e})，降级本地hash兜底"
        else:
            self.engine_type = "未配置 EMBED_API_KEY/EMBED_BASE_URL，降级本地hash兜底"

    # ---- 缓存：以"文本 sha1"为键 ----
    # 为什么用内容哈希而不是自增 id：同一文本无论来自哪次运行、哪个脚本，
    # 只要内容一致就命中缓存，保证建库/评测/inspect 三个脚本共享同一份向量缓存。
    def _cache_path(self, text: str) -> Optional[Path]:
        if not self._cache_dir:
            return None
        return self._cache_dir / f"{hashlib.sha1(text.encode('utf-8')).hexdigest()}.json"

    def _cache_get(self, text: str) -> Optional[List[float]]:
        p = self._cache_path(text)
        if p and p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                # 缓存文件损坏时静默按未命中处理，后续会重算覆盖
                return None
        return None

    def _cache_put(self, text: str, vec: List[float]):
        p = self._cache_path(text)
        if p:
            p.write_text(json.dumps(vec), encoding="utf-8")

    # ---- API：OpenAI 兼容 /embeddings 协议 ----
    def _call_api(self, texts: List[str]) -> List[List[float]]:
        # 服务端返回的 data 顺序不一定与请求一致，必须按 index 重排回输入顺序
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.cfg['base_url'].rstrip('/')}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.cfg['api_key']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]

    @staticmethod
    def _fallback_vector(text: str, dim: int = 768) -> List[float]:
        """词频-散列拟合嵌入：断网/无 key 时保证流水线可完整跑通。
        注意：仅用于演示流程不中断，无真实语义，生产环境绝不能依赖。"""
        vec = [0.0] * dim
        for i, ch in enumerate(text):
            h = int(hashlib.md5(ch.encode("utf-8")).hexdigest(), 16)
            vec[h % dim] += 1.0 / (1.0 + (i % 5))
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    # ---- LangChain Embeddings 协议（Chroma 只认这两个方法名）----
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入。流程：先查缓存 -> 未命中者按 batch_size 分批请求 -> 写回缓存。
        任一单批失败仅该批降级，不影响整库构建。"""
        vectors: List[Optional[List[float]]] = [None] * len(texts)
        pending: List[Tuple[int, str]] = []  # (原始下标, 文本)，保持最终顺序与输入一致

        for i, t in enumerate(texts):
            cached = self._cache_get(t)
            if cached is not None:
                vectors[i] = cached
            else:
                pending.append((i, t))

        if pending and self.available:
            for start in range(0, len(pending), self.batch_size):
                batch = pending[start:start + self.batch_size]
                try:
                    results = self._call_api([t for _, t in batch])
                except Exception as e:
                    print(f"       ⚠️ KSP embedding 调用失败，本批降级 hash 兜底：{e}")
                    for idx, t in batch:
                        vectors[idx] = self._fallback_vector(t)
                    continue
                for (idx, t), vec in zip(batch, results):
                    vectors[idx] = vec
                    self._cache_put(t, vec)

        # 兜底：缓存未命中且 API 不可用（或 self.available=False）时的降级
        for i, v in enumerate(vectors):
            if v is None:
                v = self._fallback_vector(texts[i])
                vectors[i] = v
                self._cache_put(texts[i], v)
        return vectors

    def embed_query(self, text: str) -> List[float]:
        """单条查询嵌入（检索时调用）。同样先查缓存。"""
        cached = self._cache_get(text)
        if cached is not None:
            return cached
        if self.available:
            try:
                vec = self._call_api([text])[0]
                self._cache_put(text, vec)
                return vec
            except Exception as e:
                print(f"       ⚠️ KSP query embedding 失败，降级 hash 兜底：{e}")
        return self._fallback_vector(text)


# ==============================================================================
# 1. Wiki 结构感知切块与元数据深度注入管道
# ==============================================================================

