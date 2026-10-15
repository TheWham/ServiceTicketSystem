"""Cross-Encoder 重排适配器（KSP 网关 /rerank 或直连供应商 + 启发式兜底）。"""

import re
import json
import time
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from ..config import load_rerank_config
from .tokenizer import ChineseTokenizer


class KspReranker:
    """
    KSP 重排模型适配器（默认 qwen3-reranker-8b，Jina 风格 /rerank 协议）：
    - 首选调用 KSP OpenAI 兼容 /rerank 端点，返回 relevance_score
    - 端点不可用时无缝降级为本地启发式交叉对齐打分，确保流水线 100% 可运行
    """

    def __init__(
        self,
        model_name: str = "qwen3-reranker-8b",
        cfg: Optional[Dict[str, str]] = None,
        backend: str = "dashscope",
        backend_retries: int = 20,
        hedge_fanout: int = 4
    ):
        self.model_name = model_name
        self.backend = backend
        self.backend_retries = backend_retries
        self.hedge_fanout = max(1, hedge_fanout) if backend != "any" else 1
        self.backend_stats = {"attempts": 0, "calls": 0, "rate_limited": 0}
        # last_used_remote 是线程本地状态：服务化后多请求共用同一 KspReranker 实例，
        # 若为实例属性，并发请求会互相污染（A 线程降级启发式会把 B 线程的远程成功
        # 覆盖成 False，导致 hybrid.py 的拒答/门控判定误判）。
        self._local = threading.local()
        self.cfg = cfg or load_rerank_config()
        self.provider = self.cfg.get("provider", "ksp")
        if self.cfg.get("note"):
            print(f"       ⚠️ {self.cfg['note']}")
        if self.provider != "ksp":
            self.backend, self.hedge_fanout = "any", 1
        self._pool = ThreadPoolExecutor(max_workers=max(1, self.hedge_fanout))
        self.endpoint = None
        api_key = self.cfg.get("api_key", "")
        self.available = bool(
            api_key
            and not api_key.startswith("sk-replace-")
            and api_key != "sk-..."
            and self.cfg.get("base_url")
        )

        if self.available:
            try:
                self.endpoint = self._resolve_endpoint()
                via = (f"KSP 网关，限定后端 {self.backend}" if self.provider == "ksp"
                       else f"直连 {self.endpoint}")
                print(f"       -> 成功加载生产级重排模型: 【{model_name}】({via})")
            except Exception as e:
                self.available = False
                print(f"       -> rerank 服务不可用({e})，降级启发式交叉对齐打分")
        else:
            print(f"       -> 未配置有效 rerank 服务地址/key（RERANK_*），采用本地启发式交叉对齐重排打分")

    @property
    def last_used_remote(self) -> bool:
        """本次 predict 是否真正走了远程 Cross-Encoder（线程本地，未打分默认 False）。"""
        return getattr(self._local, "last_used_remote", False)

    @last_used_remote.setter
    def last_used_remote(self, value: bool) -> None:
        self._local.last_used_remote = bool(value)

    def _candidate_endpoints(self) -> List[str]:
        base = self.cfg["base_url"].rstrip("/")
        if base.endswith("/rerank") or base.endswith("/reranks"):
            return [base]
        if self.provider == "ksp":
            return [f"{base}/rerank"]
        cands = []
        if "/compatible-mode/" in base:
            cands.append(base.replace("/compatible-mode/", "/compatible-api/") + "/reranks")
        cands += [f"{base}/reranks", f"{base}/rerank"]
        return list(dict.fromkeys(cands))

    def _resolve_endpoint(self) -> str:
        errors = []
        for url in self._candidate_endpoints():
            self.endpoint = url
            try:
                self._call_api("rerank 自检", ["a", "b"])
                return url
            except Exception as e:
                errors.append(f"{url} -> {e}")
        self.endpoint = None
        raise RuntimeError("；".join(errors))

    MAX_CHARS_PER_REQUEST = 10000  # 单次 /rerank 请求的文档总字符上限，超出自动分批（网关对超长请求易超时/截断）
    RATE_LIMIT_WAIT_BUDGET = 90.0  # 单次打分因 429 最多累计等待的秒数

    @staticmethod
    def _parse_results(res: Any):
        # KSP 网关把同名 qwen3-reranker-8b 随机分流到两种后端（2026-10-14 实测，约 7:3），
        # 响应头里没有上游标识、请求参数也影响不了分流，只能按响应格式识别：
        #   - Jina 风格 {"results": [...]}（约 70%）：对文档末尾空白极度敏感，仅去掉文末换行
        #     即可让同输入分数大幅漂移——讲义第六篇"绝对分漂移"现象的直接来源；
        #   - DashScope 风格 {"output": {"results": [...]}}（约 30%）：同输入可复现、对空白不敏感。
        # 旧代码只认顶层 results，落到 DashScope 时整组分数被静默补 0。
        if isinstance(res, list):
            return "list", res
        if "results" in res:
            return "jina", res["results"]
        if isinstance(res.get("output"), dict) and "results" in res["output"]:
            return "dashscope", res["output"]["results"]
        if isinstance(res.get("data"), list):
            return "data", res["data"]
        return "unknown", []

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {self.cfg['api_key']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _call_api(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[float]:
        if len(documents) > 1 and sum(len(d) for d in documents) > self.MAX_CHARS_PER_REQUEST:
            scores: List[float] = []
            batch: List[str] = []
            for doc in documents:
                if batch and sum(len(d) for d in batch) + len(doc) > self.MAX_CHARS_PER_REQUEST:
                    scores += self._call_api(query, batch)
                    batch = []
                batch.append(doc)
            return scores + self._call_api(query, batch)
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
        }
        if top_n:
            payload["top_n"] = top_n
        fmt, items = self._hedged_request(payload)
        if not items:
            raise RuntimeError(f"/rerank 响应无可解析的 results（格式 {fmt}）")
        self.backend_stats["calls"] += 1
        scores = [0.0] * len(documents)
        for item in items:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(documents):
                scores[idx] = float(item.get("relevance_score", item.get("score", 0.0)))
        return scores

    def _hedged_request(self, payload: Dict[str, Any]):
        """并发对冲：复用实例级线程池按轮次发出请求，返回第一个命中目标后端的 (格式, results)。

        限定 backend 时对冲等待"正确后端"出现：429 限流必须退避而不是立刻下一轮把配额烧光
        （对冲会放大请求量）；治本应由网关侧下线/修复 Jina 上游，客户端对冲平均多花约 2 次请求。
        """
        sent = 0
        waited = 0.0
        last_err: Optional[Exception] = None
        while sent < self.backend_retries and waited <= self.RATE_LIMIT_WAIT_BUDGET:
            n = min(self.hedge_fanout, self.backend_retries - sent)
            futures = [self._pool.submit(self._post, payload) for _ in range(n)]
            self.backend_stats["attempts"] += n
            backoff = 0.0
            for fut in as_completed(futures):
                try:
                    fmt, items = self._parse_results(fut.result())
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        last_err = e
                        self.backend_stats["rate_limited"] += 1
                        backoff = max(backoff, self._reset_seconds(e.headers.get("x-ratelimit-reset-requests")))
                        continue
                    if 400 <= e.code < 500:
                        body = e.read().decode("utf-8", "replace")[:300]
                        raise RuntimeError(f"HTTP {e.code} {body}") from e
                    last_err = e
                    sent += 1
                    continue
                except Exception as e:
                    last_err = e
                    sent += 1
                    continue
                if self.backend == "any" or fmt == self.backend:
                    for pending in futures:
                        if not pending.done():
                            pending.cancel()
                    return fmt, items
                sent += 1
            if backoff:
                time.sleep(backoff)
                waited += backoff
        if last_err is not None:
            raise RuntimeError(f"{sent} 次请求未拿到 {self.backend} 后端结果，最后一次错误：{last_err}")
        raise RuntimeError(f"连续 {self.backend_retries} 次未分流到 {self.backend} 后端")

    @staticmethod
    def _reset_seconds(value: Optional[str], cap: float = 10.0) -> float:
        m = re.fullmatch(r"(?:(\d+)m)?(\d+(?:\.\d+)?)s", (value or "").strip())
        secs = (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else 1.0
        return min(max(secs, 0.5), cap)

    @staticmethod
    def _heuristic(query: str, doc: str) -> float:
        """本地启发式交叉对齐打分（KSP 不可用时兜底）"""
        q_tokens = set(ChineseTokenizer.tokenize(query))
        doc_lower = doc.lower()

        hit_count = sum(1 for t in q_tokens if t in doc_lower)
        base_score = hit_count / max(len(q_tokens), 1)

        code_boost = 0.0
        for code in re.findall(r"[A-Za-z0-9_\-\#]+", query):
            if len(code) >= 2 and code.lower() in doc_lower:
                code_boost += 0.25

        density_boost = 0.0
        for i in range(len(query) - 3):
            if query[i:i + 4] in doc:
                density_boost += 0.05

        for neg in ["不得", "禁止", "违规", "追回", "停止", "覆盖", "解锁"]:
            if neg in query and neg in doc:
                code_boost += 0.15

        return round(min(0.99, base_score * 0.5 + code_boost + min(density_boost, 0.25) + 0.05), 4)

    def predict(self, pairs: List[List[str]]) -> List[float]:
        results: List[Optional[float]] = [None] * len(pairs)
        self.last_used_remote = True
        groups: Dict[str, List[int]] = {}
        for i, (q, _d) in enumerate(pairs):
            groups.setdefault(q, []).append(i)

        for q, idxs in groups.items():
            docs = [pairs[i][1] for i in idxs]
            if self.available:
                try:
                    scores = self._call_api(q, docs)
                    for i, s in zip(idxs, scores):
                        results[i] = s
                    continue
                except Exception as e:
                    print(f"       ⚠️ rerank 调用失败，本组降级启发式打分：{e}")
            self.last_used_remote = False
            for i in idxs:
                results[i] = self._heuristic(q, pairs[i][1])
        return [r if r is not None else 0.0 for r in results]
