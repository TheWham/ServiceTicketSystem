# -*- coding: utf-8 -*-
"""版本消歧：给定主题与时间点，解析出该时刻有效的规约版本。

## 为什么需要它，而不是复用 default_exclude

现有的「版本冲突消歧」是**召回前置的元数据物理屏蔽**——`retrieval.default_exclude`
拦掉 `wiki_status ∈ {已废止, 已下线}` 的卡，精排根本见不到旧版。那解决的是
「别把废止做法教给员工」。

本模块解决的是另一个问题：**「在某个时间点，哪一版规约是有效的」**。
它必须**看得见旧版卡**，才能判断旧版在那一刻是否还有效——所以检索时要显式
`include_excluded=True` 绕过屏蔽。两者需求相反，不能共用一套召回配置。

## 输出语义

四种结论，不互相冒充（`PolicyResolution.status`）：

- `RESOLVED`              —— 选中了该时刻有效的一版，带版本号、生效日与溯源角标；
- `NO_EFFECTIVE_VERSION`  —— 找到候选，但它们在该时刻都还没生效（制度尚未出台）；
- `UNDATED`               —— 候选里没有任何一张带生效日期，**无法**做时间判定，不猜；
- `NO_MATCH`              —— 检索零命中。

`UNDATED` 是这套设计里最容易被忽略、也最要紧的一态：本仓库 39 张卡里只有 3 组
6 张带 `effective_date`（课程构造的演示数据，见 README），其余 33 张没有日期。
对没日期的卡，唯一诚实的回答是「无法判定」，而不是默认它永远有效。
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

RESOLVED = "RESOLVED"
NO_EFFECTIVE_VERSION = "NO_EFFECTIVE_VERSION"
UNDATED = "UNDATED"
NO_MATCH = "NO_MATCH"

# 元数据里 list/dict 值是 json.dumps 后的字符串（见 chunking/parent_child.py）
_REPLACES_KEY = "wiki_replaces"
_EFFECTIVE_KEY = "wiki_effective_date"
_STATUS_KEY = "wiki_status"
_VERSION_KEY = "wiki_version"
_TITLE_KEY = "wiki_title"
_ID_KEY = "parent_id"


@dataclass(frozen=True)
class PolicyCandidate:
    """一张候选知识卡（同一张卡的多个切片已归并）。"""

    article_id: str
    title: str
    version: str
    status: str
    effective_date: Optional[str]
    replaces: Sequence[str]
    superseded_at: Optional[str]
    content: str
    score: float

    @property
    def citation(self) -> str:
        """须携带的溯源角标：`[来源: <卡号>@<版本> 《<标题>》]`。

        没有版本号时省略 `@版本` 段——宁可少写，不拼一个空的 `@`。
        """
        suffix = f"@{self.version}" if self.version else ""
        return f"[来源: {self.article_id}{suffix} 《{self.title}》]"

    def to_dict(self) -> Dict[str, Any]:
        """对外 JSON（camelCase）。不含 content——候选列表只用于人工核对。"""
        return {
            "articleId": self.article_id,
            "title": self.title,
            "version": self.version,
            "status": self.status,
            "effectiveDate": self.effective_date,
            "replaces": list(self.replaces),
            "supersededAt": self.superseded_at,
            "citation": self.citation,
            "score": round(self.score, 4),
        }


@dataclass(frozen=True)
class PolicyResolution:
    """一次消歧的完整结论。

    **先看 `status` 再读其余字段**：只有 `RESOLVED` 时 `citation` / `article_id` /
    `version` / `content` 才有值；其余三态这些字段一律为 None。
    这一点是刻意的——不让调用方从「字段是否为空」去猜结论，直接读 `status`。

    `chain` 是判定所依据的版本链（便于人工核对与现场讲解），
    `candidates` 是本次检索捞回的全部卡片（含链外的不相关卡），
    `undated_articles` 是链内「有被召回、但没有生效日期」的卡号。
    """

    status: str
    citation: Optional[str] = None
    article_id: Optional[str] = None
    title: Optional[str] = None
    version: Optional[str] = None
    effective_date: Optional[str] = None
    superseded_at: Optional[str] = None
    replaced_articles: Sequence[str] = field(default_factory=tuple)
    content: Optional[str] = None
    reason: str = ""
    candidates: Sequence[PolicyCandidate] = field(default_factory=tuple)
    chain: Sequence[PolicyCandidate] = field(default_factory=tuple)
    undated_articles: Sequence[str] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        """对外 JSON（camelCase），可直接作为 HTTP 响应的 data。"""
        return {
            "status": self.status,
            "citation": self.citation,
            "articleId": self.article_id,
            "title": self.title,
            "version": self.version,
            "effectiveDate": self.effective_date,
            "supersededAt": self.superseded_at,
            "replacedArticles": list(self.replaced_articles),
            "content": self.content,
            "reason": self.reason,
            "undatedArticles": list(self.undated_articles),
            "chain": [c.to_dict() for c in self.chain],
            "candidates": [c.to_dict() for c in self.candidates],
        }


def _as_date(value: Any) -> Optional[date]:
    """把 'YYYY-MM-DD' / date / datetime 解析成 date；无法解析返回 None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _as_str_list(raw: Any) -> List[str]:
    """元数据里的 list 是 json 字符串；解析失败按「没有」处理，不猜。"""
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if str(x).strip()]
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(x) for x in parsed if str(x).strip()]


def _first_str(value: Any) -> Optional[str]:
    """取字符串值；`None` 与**空白串**都按「没有这个字段」处理。

    元数据里的空串与字段缺失在语义上等价——区分它们只会让下游到处写空串判断。
    """
    return None if value is None else (str(value).strip() or None)


class PolicyResolver:
    """在已装配的检索器之上做版本消歧。

    装配（语料 / 向量库 / 精排器）由调用方负责——`rag_service.assembly.ServiceAssembly`
    已经做了这件事，本类不重复造一份装配，只消费它的 retriever 与 corpus。
    """

    def __init__(self, retriever):
        """:param retriever: 已装配的 `IndustrialHybridRetriever`，本类只调它的检索方法。

        不需要语料列表：检索返回的 metadata 里已经带了 `parent_id` /
        `parent_content` / `wiki_*` 全字段，判定所需的一切都在其中。
        """
        self.retriever = retriever

    # ------------------------------------------------------------------ 入口

    def resolve(self, query: str, at: Optional[Any] = None, top_k: int = 8,
                config: Optional[Dict[str, Any]] = None) -> PolicyResolution:
        """解析 `query` 主题在 `at` 时刻（默认今天）适用的规约版本。

        :param at: 时间点，接受 'YYYY-MM-DD' / date / datetime；None 取当天（UTC）。
        :param config: 检索参数覆盖（rrf_k / rough_top_k / reject_threshold 等），
                       默认取 `rag_pipeline.config` 的当前配置。
        """
        at_date = _as_date(at) or datetime.now(timezone.utc).date()

        raw = self._search(query, top_k, config or {})
        candidates = self._merge(raw)
        if not candidates:
            return PolicyResolution(
                status=NO_MATCH,
                reason=f"检索零命中：没有与「{query}」相关的知识卡片")

        # 先算出每张卡「何时被取代」，供调用方理解新旧关系
        superseded = self._supersede_map(candidates)
        candidates = [
            PolicyCandidate(**{**c.__dict__, "superseded_at": superseded.get(c.article_id)})
            for c in candidates
        ]

        # 沿**命中主题**的版本链选版本，而不是在所有候选里挑日期最大的：
        # 一次检索会捎回若干不相关卡片，全局取 max 会让「同日期同版本号」的两条链
        # 按遍历顺序任选其一（不稳定）。先按相关度定主题，再在它的链内判时间。
        seed = max(candidates, key=lambda c: c.score)
        chain = self._chain(seed.article_id, candidates)

        dated = [c for c in chain if _as_date(c.effective_date) is not None]
        undated_ids = [c.article_id for c in chain if _as_date(c.effective_date) is None]

        if not dated:
            return PolicyResolution(
                status=UNDATED,
                reason=(f"主题命中 {seed.article_id}，但其版本链上的 {len(chain)} 张卡都没有"
                        f"生效日期，无法判断 {at_date.isoformat()} 时刻哪一版有效——不猜。"),
                candidates=tuple(candidates),
                chain=tuple(chain),
                undated_articles=tuple(undated_ids))

        effective = [c for c in dated if _as_date(c.effective_date) <= at_date]
        if not effective:
            earliest = min(dated, key=lambda c: _as_date(c.effective_date))
            return PolicyResolution(
                status=NO_EFFECTIVE_VERSION,
                reason=(f"{at_date.isoformat()} 时刻尚无生效版本：相关规约最早的 "
                        f"{earliest.article_id} 也要到 {earliest.effective_date} 才生效。"),
                candidates=tuple(candidates),
                chain=tuple(chain),
                undated_articles=tuple(undated_ids))

        chosen = max(effective, key=lambda c: (_as_date(c.effective_date), c.version))
        return PolicyResolution(
            status=RESOLVED,
            citation=chosen.citation,
            article_id=chosen.article_id,
            title=chosen.title,
            version=chosen.version,
            effective_date=chosen.effective_date,
            superseded_at=chosen.superseded_at,
            replaced_articles=tuple(chosen.replaces),
            content=chosen.content,
            reason=(f"{at_date.isoformat()} 时刻适用 {chosen.article_id} {chosen.version}"
                    f"（自 {chosen.effective_date} 起生效）"),
            candidates=tuple(candidates),
            chain=tuple(chain),
            undated_articles=tuple(undated_ids))

    # ------------------------------------------------------------------ 内部

    def _search(self, query: str, top_k: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """召回候选——**必须 include_excluded=True**，否则看不见废止卡，无从消歧。"""
        from .config import load_config
        cfg = load_config()
        rc = cfg.retrieval
        return self.retriever.hybrid_rerank_search(
            query=query,
            final_top_k=top_k,
            rrf_k=config.get("rrf_k", rc.rrf_k),
            rough_top_k=config.get("rough_top_k", rc.rough_top_k),
            fuse_k=config.get("fuse_k", rc.fuse_k),
            rrf_weight=config.get("rrf_weight", rc.rrf_weight),
            rerank_weight=config.get("rerank_weight", rc.rerank_weight),
            metadata_filter=config.get("metadata_filter"),
            # 消歧要自己判时间，不能在召回阶段就把废止卡掐掉
            reject_threshold=None,
            heuristic_reject_threshold=None,
            rerank_granularity=rc.rerank_granularity,
            include_excluded=True,
        )

    def _merge(self, search_res: Dict[str, Any]) -> List[PolicyCandidate]:
        """把同一张卡的多个切片归并成一条候选。"""
        by_card: Dict[str, Dict[str, Any]] = {}
        for item in (search_res or {}).get("final_results") or []:
            md = item.get("metadata") or {}
            article_id = _first_str(md.get(_ID_KEY)) or _first_str(md.get("wiki_id"))
            if not article_id:
                continue
            key = article_id
            score = float(item.get("rerank_score") or 0.0)
            content = md.get("parent_content") or item.get("content") or ""
            existing = by_card.get(key)
            if existing is None or score > existing["score"]:
                by_card[key] = {
                    "article_id": article_id,
                    "title": _first_str(md.get(_TITLE_KEY)) or _first_str(md.get("Header_1")) or article_id,
                    "version": _first_str(md.get(_VERSION_KEY)) or "",
                    "status": _first_str(md.get(_STATUS_KEY)) or "现行",
                    "effective_date": _first_str(md.get(_EFFECTIVE_KEY)),
                    "replaces": _as_str_list(md.get(_REPLACES_KEY)),
                    "content": content,
                    "score": score,
                }
        return [PolicyCandidate(**v, superseded_at=None) for v in by_card.values()]

    @staticmethod
    def _chain(seed_id: str, candidates: Sequence[PolicyCandidate]) -> List[PolicyCandidate]:
        """返回 `seed_id` 所在的版本链：它自己 + 它取代的旧版 + 取代它的新版。

        只沿 `replaces` 这条已声明的边连接，不做标题/关键词的软匹配——
        猜出来的版本关系会悄悄把不相干的卡串成一链，比「没有关系」更危险。
        """
        by_id = {c.article_id: c for c in candidates}
        ids = {seed_id} if seed_id in by_id else set()

        # 向上：谁声明取代了链上的某张卡
        changed = True
        while changed:
            changed = False
            for c in candidates:
                if c.article_id not in ids and set(c.replaces) & ids:
                    ids.add(c.article_id)
                    changed = True

        # 向下：链上的卡声明取代了谁
        changed = True
        while changed:
            changed = False
            for aid in list(ids):
                for old in by_id[aid].replaces:
                    if old in by_id and old not in ids:
                        ids.add(old)
                        changed = True

        return [by_id[i] for i in sorted(ids)]

    @staticmethod
    def _supersede_map(candidates: Sequence[PolicyCandidate]) -> Dict[str, str]:
        """卡 A 的 replaces 里含卡 B → B 在 A 生效日被取代。"""
        out: Dict[str, str] = {}
        for c in candidates:
            date = _as_date(c.effective_date)
            if date is None:
                continue
            for old_id in c.replaces:
                out.setdefault(old_id, c.effective_date)
        return out