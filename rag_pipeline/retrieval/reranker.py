"""Cross-Encoder 重排适配器（KSP 网关 /rerank 或直连供应商 + 启发式兜底）。"""

import re
import json
import time
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

    ⚠️ 重要工程约束（详见讲义第六篇）：
    远程 Reranker 的**绝对分**可能不稳定（同输入多次调用分数区间会漂移），
    但**排序**基本稳定。因此下游 hybrid_rerank_search 只取它的"名次"做融合，
    不直接信任绝对分，避免分数漂移导致结果抖动。
    （后续定位：漂移的真实根因是网关在两种后端间切换，见下方 _parse_results 前的注释。）
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
        # backend：只接受哪种后端的打分（dashscope | jina | any）；非目标后端的响应丢弃重试
        self.backend = backend
        self.backend_retries = backend_retries
        # 对冲并发数：每轮同时发 hedge_fanout 个相同请求，取第一个命中目标后端的响应。
        # 串行重试时目标后端只占约 30% 流量，长尾可达 7~8 秒；并发对冲把多数请求压回单轮耗时
        self.hedge_fanout = max(1, hedge_fanout) if backend != "any" else 1
        # 后端命中统计：attempts=总请求数，calls=成功返回的打分次数（供评测报告核对开销）
        self.backend_stats = {"attempts": 0, "calls": 0, "rate_limited": 0}
        # 最近一次 predict 是否全部来自远程打分（False=至少一组降级为启发式，分数量纲不同）
        self.last_used_remote = False
        self.cfg = cfg or load_rerank_config()
        self.provider = self.cfg.get("provider", "ksp")
        if self.cfg.get("note"):
            print(f"       ⚠️ {self.cfg['note']}")
        # 双后端限定与对冲只针对 KSP 网关；直连供应商只有一个后端，单发即可
        if self.provider != "ksp":
            self.backend, self.hedge_fanout = "any", 1
        self.endpoint = None
        self.available = bool(self.cfg["api_key"] and self.cfg["base_url"])

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
            print(f"       -> 未配置 rerank 服务地址/key（RERANK_*），采用本地启发式交叉对齐重排打分")

    def _candidate_endpoints(self) -> List[str]:
        """按供应商约定推导 rerank 端点候选。

        - KSP 网关：{base}/rerank（Jina 协议）
        - 阿里云百炼：OpenAI 兼容重排不在 Chat 用的 /compatible-mode/v1 下，
          而在 /compatible-api/v1/reranks（复数）；用户填 Chat 的 base_url 也能自动换算
        - 其他兼容服务：{base}/rerank 或 {base}/reranks
        """
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
        """逐个探测候选端点，返回第一个能解析出打分结果的；全部失败则抛出各端点的错误。"""
        errors = []
        for url in self._candidate_endpoints():
            self.endpoint = url
            try:
                self._call_api("rerank 自检", ["a", "b"])
                return url
            except Exception as e:
                errors.append(f"{url} -> {e}")
        self.endpoint = None  # 全部探测失败：不残留最后一个（多半是 404 的）候选地址
        raise RuntimeError("；".join(errors))

    # KSP 网关把同名 qwen3-reranker-8b 随机分流到两种后端（2026-10-14 实测，约 7:3），
    # 响应头里没有上游标识、请求参数也影响不了分流，只能按响应格式识别：
    #   - Jina 风格 {"results": [...]}（约 70%）：对文档末尾空白极度敏感（仅去掉文末换行，
    #     目标卡分数 0.78→0.37），疑似服务端未套用 Qwen3-Reranker 的提示模板、分数取决于末 token；
    #     20 题评测纯精排卡级 MRR 0.81，正负样本分数重叠（AUC 0.76）。
    #   - DashScope 风格 {"output": {"results": [...]}}（约 30%）：同输入可复现、对空白不敏感；
    #     纯精排 MRR 1.00，正样本 Top-1 分 ≥0.47、库外负样本 ≤0.27，可干净切分（AUC 1.00）。
    # 旧代码只认顶层 results，落到 DashScope 时整组分数被静默补 0——讲义第六篇"绝对分漂移"的真实根因。
    # 处理：两种格式都解析；只接受 self.backend 指定后端的打分，其余丢弃重试，
    # 保证同一轮评测的分数来自同一后端、且是质量正常的那个。
    # ⚠️ 治本应由网关侧下线/修复 Jina 上游；客户端重试平均多花约 2 次请求。

    MAX_CHARS_PER_REQUEST = 10000
    RATE_LIMIT_WAIT_BUDGET = 90.0   # 单次打分因 429 最多累计等待的秒数

    @staticmethod
    def _parse_results(res: Any):
        """返回 (后端格式, results 列表)；每项需含 index 与 relevance_score（或 score）。"""
        if isinstance(res, list):  # TEI 等直接返回列表
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
        """调用 rerank 端点，返回与输入 documents 同序的相关度分数列表。

        服务端返回 results 里每项带 index 与 relevance_score，顺序不一定与请求一致，
        必须按 index 还原回输入顺序，否则下游会把分数错配到错误的文档上。
        解析不到任何结果时抛异常（交给 predict 降级），绝不静默返回全 0。

        单次请求文本过长时按 MAX_CHARS_PER_REQUEST 分批：KSP dashscope 后端在单请求约 2.7 万字时
        会截断文档、分数随之改变（同一张卡同批 1~16 张时恒为 0.4456，35 张时变 0.3371，2026-10-14 实测），
        分批后每篇文档的分数与单独打分一致。Cross-Encoder 逐篇独立打分，分批不改变语义。
        """
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
        # 按返回的 index 还原为与输入 documents 同序
        scores = [0.0] * len(documents)
        for item in items:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(documents):
                scores[idx] = float(item.get("relevance_score", item.get("score", 0.0)))
        return scores

    def _hedged_request(self, payload: Dict[str, Any]):
        """并发对冲：按轮次同时发出多个相同请求，返回第一个命中目标后端的 (格式, results)。"""
        sent = 0          # 计入重试预算的请求数（拿到了响应但不是目标后端/服务端 5xx 等）
        waited = 0.0      # 因 429 限流累计等待的秒数
        last_err: Optional[Exception] = None
        # 不用 with：拿到目标响应即返回，同轮其余在途请求不等待（shutdown(wait=False)）
        pool = ThreadPoolExecutor(max_workers=self.hedge_fanout)
        try:
            while sent < self.backend_retries and waited <= self.RATE_LIMIT_WAIT_BUDGET:
                n = min(self.hedge_fanout, self.backend_retries - sent)
                futures = [pool.submit(self._post, payload) for _ in range(n)]
                self.backend_stats["attempts"] += n
                backoff = 0.0
                for fut in as_completed(futures):
                    try:
                        fmt, items = self._parse_results(fut.result())
                    except urllib.error.HTTPError as e:
                        # 429 限流：对冲会放大请求量，必须退避而不是立刻下一轮把配额烧光。
                        # 限流不代表"没分到目标后端"，不消耗重试预算，只受等待总时长约束——
                        # 否则一阵限流就把预算烧光、整题静默降级成启发式打分
                        if e.code == 429:
                            last_err = e
                            self.backend_stats["rate_limited"] += 1
                            backoff = max(backoff, self._reset_seconds(e.headers.get("x-ratelimit-reset-requests")))
                            continue
                        # 其余 4xx（参数错/鉴权失败/路径不存在）重试也不会好：立刻带上服务端报错体抛出
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
                        return fmt, items
                    sent += 1
                if backoff:
                    time.sleep(backoff)
                    waited += backoff
        finally:
            pool.shutdown(wait=False)
        if last_err is not None:
            raise RuntimeError(f"{sent} 次请求未拿到 {self.backend} 后端结果，最后一次错误：{last_err}")
        raise RuntimeError(f"连续 {self.backend_retries} 次未分流到 {self.backend} 后端")

    @staticmethod
    def _reset_seconds(value: Optional[str], cap: float = 10.0) -> float:
        """解析限流重置时间（如 "4s"、"1m0s"），缺省 1 秒，最多等 cap 秒。"""
        m = re.fullmatch(r"(?:(\d+)m)?(\d+(?:\.\d+)?)s", (value or "").strip())
        secs = (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else 1.0
        return min(max(secs, 0.5), cap)

    @staticmethod
    def _heuristic(query: str, doc: str) -> float:
        """本地启发式交叉对齐打分（KSP 不可用时兜底）"""
        q_tokens = set(ChineseTokenizer.tokenize(query))
        doc_lower = doc.lower()

        # 1. 基础词项召回覆盖率
        hit_count = sum(1 for t in q_tokens if t in doc)
        base_score = hit_count / max(len(q_tokens), 1)

        # 2. 精确编码与数字硬命中增强
        code_boost = 0.0
        for code in re.findall(r"[A-Za-z0-9_\-\#]+", query):
            if len(code) >= 2 and code.lower() in doc_lower:
                code_boost += 0.25

        # 3. 连续子串密集度
        density_boost = 0.0
        for i in range(len(query) - 3):
            if query[i:i+4] in doc:
                density_boost += 0.05

        # 4. 否定/处置类词敏感度
        for neg in ["不得", "禁止", "违规", "追回", "停止", "覆盖", "解锁"]:
            if neg in query and neg in doc:
                code_boost += 0.15

        return round(min(0.99, base_score * 0.5 + code_boost + min(density_boost, 0.25) + 0.05), 4)

    def predict(self, pairs: List[List[str]]) -> List[float]:
        """对 (query, doc) 对列表打分，返回与输入同序的分数列表。

        同一 query 的多篇候选合并为一次 /rerank 请求（减少往返）；
        若该次调用失败，仅这一组降级为启发式打分，不影响其他查询。
        """
        results: List[Optional[float]] = [None] * len(pairs)
        self.last_used_remote = True
        # 同一 query 的多篇文档合并为一次请求
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


# ==============================================================================
# 2. 生产级双路混合检索与 RRF 融合重排器 (IndustrialHybridRetriever)
# ==============================================================================

