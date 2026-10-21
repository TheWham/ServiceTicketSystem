"""KSP OpenAI 兼容嵌入提供者与配置加载（自索引构建流水线平移）。"""

import os
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Embedding 配置统一走 config.load_embedding_config（独立 EMBED_API_KEY/EMBED_BASE_URL/EMBED_MODEL）
from .config import load_embedding_config

# 常见嵌入模型的标准向量维度映射（兜底向量必须与目标模型维度严格一致，防止 Chroma 维度冲突崩溃）
MODEL_DIMENSIONS: Dict[str, int] = {
    "qwen3-embedding-8b": 4096,
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
    "bge-large-zh-v1.5": 1024,
    "bge-m3": 1024,
}


class KspEmbeddingProvider:
    """
    KSP OpenAI 兼容 /embeddings 提供者（默认 qwen3-embedding-8b，4096 维）：
    - 批量请求降低往返开销
    - 磁盘缓存（按 model + text 的 sha1，向后兼容旧版纯 text sha1 缓存），重跑零 API 成本
    - 接口异常时自动降级同维度 hash 兜底向量（绝不写入磁盘缓存，防止缓存投毒），保证流水线不中断
    """

    def __init__(self, cfg: Optional[Dict[str, str]] = None, cache_dir: Optional[str] = None,
                 batch_size: int = 32, model_override: Optional[str] = None):
        self.cfg = cfg or load_embedding_config()
        self.model = model_override or self.cfg["model"]
        self.dim = MODEL_DIMENSIONS.get(self.model, 4096)
        self.batch_size = batch_size
        # 过滤模板占位符 key（如 sk-... 或 sk-replace-...）
        api_key = self.cfg.get("api_key", "")
        self.available = bool(
            api_key
            and not api_key.startswith("sk-replace-")
            and api_key != "sk-..."
            and self.cfg.get("base_url")
        )
        self._cache_dir = Path(cache_dir) if cache_dir else None
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        if self.available:
            # 首次自检，失败则降级
            try:
                probe_vec = self._call_api(["embedding 自检"])[0]
                if probe_vec:
                    self.dim = len(probe_vec)
                self.engine_type = f"KSP OpenAI兼容 /embeddings ({self.model})"
            except Exception as e:
                self.available = False
                self.engine_type = f"KSP 不可用({e})，降级本地hash兜底({self.dim}维)"
        else:
            self.engine_type = f"未配置有效 EMBED_API_KEY/EMBED_BASE_URL，降级本地hash兜底({self.dim}维)"

    # ---- 缓存：以"模型名 + 文本 sha1"为键（同时兼容读取旧版纯文本 sha1 缓存） ----
    def _cache_path(self, text: str) -> Optional[Path]:
        if not self._cache_dir:
            return None
        key = hashlib.sha1(f"{self.model}\n{text}".encode("utf-8")).hexdigest()
        return self._cache_dir / f"{key}.json"

    def _legacy_cache_path(self, text: str) -> Optional[Path]:
        if not self._cache_dir:
            return None
        return self._cache_dir / f"{hashlib.sha1(text.encode('utf-8')).hexdigest()}.json"

    def _cache_get(self, text: str) -> Optional[List[float]]:
        for p in (self._cache_path(text), self._legacy_cache_path(text)):
            if p and p.exists():
                try:
                    vec = json.loads(p.read_text(encoding="utf-8"))
                    # 校验向量维度与当前模型维度一致，防止旧 768 维脏兜底向量污染 4096 维库
                    if isinstance(vec, list) and len(vec) == self.dim:
                        return vec
                except Exception:
                    continue
        return None

    def _cache_put(self, text: str, vec: List[float]):
        p = self._cache_path(text)
        if p and len(vec) == self.dim:
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
        vecs = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
        if vecs and vecs[0]:
            self.dim = len(vecs[0])
        return vecs

    @staticmethod
    def _fallback_vector(text: str, dim: int = 4096) -> List[float]:
        """词频-散列拟合嵌入：断网/无 key 时保证流水线可完整跑通。
        注意：维度默认对齐 qwen3-embedding-8b (4096 维)，且绝不写入磁盘缓存以防缓存投毒。"""
        vec = [0.0] * dim
        for i, ch in enumerate(text):
            h = int(hashlib.md5(ch.encode("utf-8")).hexdigest(), 16)
            vec[h % dim] += 1.0 / (1.0 + (i % 5))
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    # ---- LangChain Embeddings 协议（Chroma 只认这两个方法名）----
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入。流程：先查缓存 -> 未命中者按 batch_size 分批请求 -> 真实向量写回缓存。
        任一单批失败仅该批降级为同维度 hash 兜底向量（不写缓存），不影响整库构建。"""
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
                    print(f"       ⚠️ KSP embedding 调用失败，本批降级 hash 兜底({self.dim}维)：{e}")
                    for idx, t in batch:
                        vectors[idx] = self._fallback_vector(t, dim=self.dim)
                    continue
                for (idx, t), vec in zip(batch, results):
                    vectors[idx] = vec
                    self._cache_put(t, vec)

        # 兜底：缓存未命中且 API 不可用时的降级（注意：绝不调用 _cache_put，防止假向量污染磁盘缓存）
        for i, v in enumerate(vectors):
            if v is None:
                vectors[i] = self._fallback_vector(texts[i], dim=self.dim)
        return vectors

    def embed_query(self, text: str) -> List[float]:
        """单条查询嵌入（检索时调用）。同样先查缓存，降级向量不写缓存。"""
        cached = self._cache_get(text)
        if cached is not None:
            return cached
        if self.available:
            try:
                vec = self._call_api([text])[0]
                self._cache_put(text, vec)
                return vec
            except Exception as e:
                print(f"       ⚠️ KSP query embedding 失败，降级 hash 兜底({self.dim}维)：{e}")
        return self._fallback_vector(text, dim=self.dim)
