"""KSP Cross-Encoder 重排适配器（/rerank 协议 + 启发式兜底）。"""

import re
import json
import urllib.request
from typing import List, Dict, Any, Optional

from ..embedding import load_ksp_config
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
    """

    def __init__(self, model_name: str = "qwen3-reranker-8b", cfg: Optional[Dict[str, str]] = None):
        self.model_name = model_name
        self.cfg = cfg or load_ksp_config()
        self.available = bool(self.cfg["api_key"] and self.cfg["base_url"])

        if self.available:
            try:
                self._call_api("rerank 自检", ["a", "b"])
                print(f"       -> 成功加载生产级重排模型: 【{model_name}】(KSP /rerank)")
            except Exception as e:
                self.available = False
                print(f"       -> KSP rerank 不可用({e})，降级启发式交叉对齐打分")
        else:
            print(f"       -> 未配置 KSP_API_KEY/KSP_BASE_URL，采用本地启发式交叉对齐重排打分")

    def _call_api(self, query: str, documents: List[str], top_n: Optional[int] = None) -> List[float]:
        """调用 KSP /rerank，返回与输入 documents 同序的相关度分数列表。

        服务端返回 results 里每项带 index 与 relevance_score，顺序不一定与请求一致，
        必须按 index 还原回输入顺序，否则下游会把分数错配到错误的文档上。
        """
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
        }
        if top_n:
            payload["top_n"] = top_n
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.cfg['base_url'].rstrip('/')}/rerank",
            data=data,
            headers={
                "Authorization": f"Bearer {self.cfg['api_key']}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        # 按返回的 index 还原为与输入 documents 同序
        scores = [0.0] * len(documents)
        for item in res.get("results", []):
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(documents):
                scores[idx] = float(item.get("relevance_score", 0.0))
        return scores

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
                    print(f"       ⚠️ KSP rerank 调用失败，本组降级启发式打分：{e}")
            for i in idxs:
                results[i] = self._heuristic(q, pairs[i][1])
        return [r if r is not None else 0.0 for r in results]


# ==============================================================================
# 2. 生产级双路混合检索与 RRF 融合重排器 (IndustrialHybridRetriever)
# ==============================================================================

