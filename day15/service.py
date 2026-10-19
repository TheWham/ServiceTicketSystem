# -*- coding: utf-8 -*-
"""EnterpriseKnowledgeService — 检索 + 受约束生成 + 结构化溯源。

一致性契约（docs/Day15 第四节）：本层不复制检索参数与切块逻辑，
检索装配整体复用 rag_service.assembly.ServiceAssembly（其构造即
load_config → 语料(build_chunker) → 指纹校验 → 向量库 → IndustrialHybridRetriever
→ QueryRewriter → 检索锁）。本层只绕过其契约映射层，直接调用
hybrid_rerank_search —— 因为演示需要 scored_all（链路可视化）与
metadata["parent_content"]（grounding 上下文），这两样契约映射层都会丢。

Citation 五字段全部取自检索命中 metadata，不依赖 LLM 是否打角标；
LLM 只负责把 [来源: 卡片id - 章节名] 写进正文，解析后仅做对齐标记。
"""

import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag_pipeline.chunking.structure_aware import WikiStructureAwareChunker
from rag_pipeline.config import build_chunker, build_gate

from rag_service.assembly import LockBusy, ServiceAssembly

from . import config as dcfg
from .llm import GroundingGenerator, OfflineError
from .prompts import OFFLINE_TEXT, REFUSAL_TEXT
from .schemas import (CardInfo, ChatResponse, ChunkChild, ChunkDemoResponse,
                      Citation, HealthResponse, Trace, TraceCandidate)

INLINE_CITATION_RE = re.compile(r"\[来源[:：]\s*([A-Za-z0-9А-Яа-я\-]+)\s*[-—–]\s*([^\]]+)\]")
REFUSAL_MARKERS = ("未记载相关内容", "知识库中未记载", "建议咨询相关主管部门")
MAX_CANDIDATES_IN_TRACE = 15
MAX_SNIPPET = 400


def _clamp_score(value: Any) -> float:
    """rerank 原始分钳制到 [0,1] 保留 4 位（与 rag_service.mapping._clamp_score 同口径）。"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(min(1.0, max(0.0, v)), 4)


def _collapse(text: Any) -> str:
    return " ".join(str(text or "").split())


def _norm_id(s: str) -> str:
    """归一化卡片 id 用于宽松匹配：去掉空格/圆点/连字符等非字母数字字符并统一大写。

    容忍 LLM 把 ITKB-ACC-002 写成「ITKB · ACC-002」「ITKB ACC-002」等变体。
    """
    return re.sub(r"[^A-Za-z0-9]", "", s or "").upper()


def parse_inline_citations(answer: str) -> List[tuple]:
    """解析正文中的 [来源: 卡片id - 章节名] 角标，返回 [(card_id, section)]。

    这是把"LLM 自由文本里的角标"抽成结构化引用的第一道解析。卡片 id 允许含
    ASCII 连字符（ITKB-ACC-002）、数字、字母；section 为 H2 小节名。
    仅做正则提取，不做存在性校验——角标是否与命中卡对齐交给 build_citations 处理。

    Args:
        answer: LLM 生成的答案正文（可能含 0~N 个角标）。

    Returns:
        [(卡片id, 章节名)] 元组列表；无角标时返回空列表。
    """
    return [(m.group(1).strip(), m.group(2).strip()) for m in INLINE_CITATION_RE.finditer(answer or "")]


def build_citations(final_results: List[Dict[str, Any]], answer: str = "") -> List[Citation]:
    """把检索命中的子块列表组装成结构化溯源 Citation 列表（两段式，防演示翻车）。

    第一段 —— 结构化基底（永远存在，不依赖 LLM）：
        对每条命中子块，直接从其 metadata 抽取五字段组装 Citation：
        chunk_id / source_file / section(H2 面包屑) / snippet(父卡片段) /
        relevance_score(rerank 分钳到 [0,1])。`rerank_granularity=parent` 时
        `item["content"]` 是子块文本，整卡全文要取 `metadata["parent_content"]`。

    第二段 —— 内联角标对齐（可选，容错）：
        若提供了 answer，解析其内联角标并把"被正文引用"标记到对应 Citation
        上（cited_inline=True），同时用角标里的章节名覆盖 section。
        匹配用归一化（_norm_id）以容忍 LLM 的 id 变体写法。

    设计要点：即便 LLM 一个角标都没打、或打的卡片 id 不存在，返回的
    Citation 列表仍完整可用，页面照常渲染"来源"区——结构化溯源不靠 LLM。

    Args:
        final_results: 内核 hybrid_rerank_search 的 final_results 列表。
        answer: （可选）LLM 生成的答案正文，用于内联角标对齐。

    Returns:
        Citation 列表（每条对应一个命中子块，按命中顺序）。
    """
    citations: List[Citation] = []
    for it in final_results:
        md = it.get("metadata") or {}
        card_id = md.get("parent_id") or md.get("wiki_id") or ""
        content = md.get("parent_content") or it.get("content") or ""
        citations.append(Citation(
            chunk_id=md.get("child_id") or md.get("chunk_id") or card_id or "unknown",
            source_file=md.get("source_file", ""),
            section=md.get("Header_2", ""),
            snippet=_collapse(content)[:MAX_SNIPPET],
            relevance_score=_clamp_score(it.get("rerank_score")),
            card_id=card_id,
            title=_collapse(md.get("Header_1") or md.get("wiki_title") or card_id),
        ))
    for cid, section in parse_inline_citations(answer):
        for c in citations:
            if c.card_id == cid or _norm_id(c.card_id) == _norm_id(cid):
                c.cited_inline = True
                if section:
                    c.section = section
    return citations


def canonicalize_answer_citations(answer: str, card_ids: List[str]) -> str:
    """把答案正文里的角标卡片 id 回正为命中的真实卡片 id。

    为什么需要：LLM 可能把规范卡片 id 写成变体（"ITKB · ACC-002"、"ITKB ACC-002"、
    大小写漂移等）。本函数按归一化（_norm_id）把变体匹配到本次实际命中的卡片 id，
    并替换正文中的角标 id 为规范形式，保证页面上渲染的角标与下方来源列表一致。

    匹配不到的角标保持原样（交由 answer() 的 notes 记录"角标引用了未命中的卡片"）。

    Args:
        answer: LLM 生成的答案正文（含角标）。
        card_ids: 本次实际命中的真实卡片 id 列表（作为回正目标集合）。

    Returns:
        角标 id 已回正为真实卡片 id 的答案正文。
    """
    canon = {}
    for c in card_ids:
        canon.setdefault(_norm_id(c), c)

    def _repl(m: "re.Match") -> str:
        cid, sec = m.group(1).strip(), m.group(2).strip()
        real = canon.get(_norm_id(cid))
        return f"[来源: {real or cid} - {sec}]"

    return INLINE_CITATION_RE.sub(_repl, answer or "")


def build_trace(res: Dict[str, Any], *, retrieval_ms: float, llm_ms: float,
                total_ms: float, reject_threshold: Optional[float]) -> Trace:
    """从 hybrid_rerank_search 返回字典组装链路快照 Trace（驱动网页漏斗可视化）。

    数据全部来自内核结构化返回，不需要 verbose 打印、不改动内核代码：
    - 漏斗各阶段数字：bm25_count / dense_count / fused_count / max_rerank_score /
      rerank_remote（是否真跑远程精排）/ gate_mode+gate_margin（置信度门控）；
    - 候选明细表：取自 scored_all，每条记录 RRF 名次 → Rerank 名次 → 融合分，
      并标记 is_final（进 Top-K）与 protected（被双路共振捞回）。

    注意：scored_all 里混有 Document 对象，此处只取标量字段（metadata/rank/score），
    保证结果可 JSON 序列化。

    Args:
        res: hybrid_rerank_search 的返回字典。
        retrieval_ms: 检索耗时（内核返回的 latency_ms）。
        llm_ms: LLM 生成耗时（服务层自测）。
        total_ms: 端到端总耗时（服务层自测）。
        reject_threshold: 拒答阈值（远程 rerank 标定值，用于页面展示）。

    Returns:
        Trace 对象（含漏斗各阶段数据 + 候选明细 + 时间分解）。
    """
    final_ids = []
    for it in res.get("final_results") or []:
        md = it.get("metadata") or {}
        final_ids.append(md.get("child_id") or md.get("chunk_id") or md.get("parent_id") or "")
    final_set = set(final_ids)

    candidates: List[TraceCandidate] = []
    for it in (res.get("scored_all") or [])[:MAX_CANDIDATES_IN_TRACE]:
        md = it.get("metadata") or {}
        cid = md.get("child_id") or md.get("chunk_id") or md.get("parent_id") or ""
        candidates.append(TraceCandidate(
            chunk_id=cid,
            card_id=md.get("parent_id") or md.get("wiki_id") or "",
            title=_collapse(md.get("Header_1") or md.get("wiki_title") or ""),
            section=md.get("Header_2", ""),
            rrf_rank=it.get("rrf_rank"),
            rerank_rank=it.get("rerank_rank"),
            rrf_score=it.get("rrf_score"),
            rerank_score=it.get("rerank_score"),
            fused_score=it.get("fused_score"),
            is_final=cid in final_set,
            protected=bool(it.get("protected")),
        ))

    return Trace(
        bm25_count=res.get("bm25_count", 0),
        dense_count=res.get("dense_count", 0),
        fused_count=res.get("fused_count", 0),
        rerank_remote=bool(res.get("rerank_remote")),
        gate_mode=res.get("gate_mode", "off"),
        gate_margin=res.get("gate_margin", 0.0),
        eff_weights=list(res.get("eff_weights") or []),
        max_rerank_score=res.get("max_rerank_score", 0.0),
        reject_threshold=reject_threshold,
        rejected=bool(res.get("rejected")),
        rewrite_query=res.get("rewrite_query"),
        candidates=candidates,
        final_ids=final_ids,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        total_ms=total_ms,
    )


class EnterpriseKnowledgeService:
    """企业知识库问答服务：复用 ServiceAssembly 检索，叠加 grounding 与 Citation。"""

    def __init__(self, generator: Optional[GroundingGenerator] = None) -> None:
        """装配服务：复用 ServiceAssembly 检索内核 + 挂 LLM 生成器 + 备好切块器。

        一致性契约的落点——`ServiceAssembly()` 的构造就是文档要求的那条装配路径
        （load_config → build_chunker → 向量库 manifest 指纹校验 → IndustrialHybridRetriever
        → QueryRewriter → 检索锁），因此本层无需、也不得再写第二套检索参数。
        指纹漂移或向量库缺失时，ServiceAssembly 会在此 fail-fast 抛错。

        Args:
            generator: 可注入的自定义生成器（测试用）；默认新建 kimi-k3 的 GroundingGenerator。
        """
        self.asm = ServiceAssembly()           # 构造即完成装配与指纹 fail-fast 校验
        self.generator = generator or GroundingGenerator()
        self._chunker, self._use_parent_child = build_chunker(self.asm.cfg)

    # ------------------------------------------------------------------ 检索

    def _search(self, query: str, top_k: Optional[int],
                metadata_filter: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """串行执行一次混合检索（复用装配体的检索锁），参数全部出自 configs/pipeline.yaml。

        演示是高并发风险的：检索内核 BM25/reranker 是有状态的进程级单例，并发进来会错乱，
        因此这里沿用装配体自带的线程锁串行执行。锁等待超时抛 LockBusy，由上层映射为 503。

        Args:
            query: 用户问题。
            top_k: 期望返回的最终命中数；None 则用 pipeline.yaml 的 retrieval.top_k。
            metadata_filter: 元数据硬过滤（如 {"wiki_category": "网络连接"}）。

        Returns:
            hybrid_rerank_search 的原始返回字典（含 final_results / scored_all / rejected 等）。

        Raises:
            LockBusy: 检索锁等待超时。
        """
        asm = self.asm
        if asm.serialize_search:
            if not asm._lock.acquire(timeout=asm.lock_wait_seconds):
                raise LockBusy(f"检索锁等待超过 {asm.lock_wait_seconds}s")
            try:
                return self._run_search(query, top_k, metadata_filter)
            finally:
                asm._lock.release()
        return self._run_search(query, top_k, metadata_filter)

    def _run_search(self, query: str, top_k: Optional[int],
                    metadata_filter: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """真正调用检索内核 hybrid_rerank_search，参数全部从 pipeline.yaml 读，零硬编码。

        完整链路（内核内部）：元数据过滤 → BM25+Dense 双路召回 → RRF 倒数排名融合 →
        Rerank(parent) 交叉精排 → 置信度动态门控按秩融合 → Top-1/2 共振保护 → 低置信拒答。
        query_rewrite 开启时先做查询改写，原查询与改写查询一起四路召回。

        Args:
            query: 用户问题。
            top_k: 最终返回条数；None 用配置 top_k。
            metadata_filter: 元数据硬过滤。

        Returns:
            内核返回字典，关键键：final_results / scored_all / rejected / rerank_remote /
            gate_mode / bm25_count / dense_count / fused_count / max_rerank_score / latency_ms。
        """
        rc = self.asm.cfg.retrieval
        rewrite = self.asm.rewriter.rewrite(query) if self.asm.rewriter else None
        return self.asm.retriever.hybrid_rerank_search(
            query=query,                                    # 用户问题原文
            final_top_k=top_k or rc.top_k,                  # 最终返回 Top-N（默认 3，交付给 LLM/页面）
            rrf_k=rc.rrf_k,                                 # RRF 倒数融合常数 k=60（Σ 1/(60+名次)）
            rough_top_k=rc.rough_top_k,                     # 粗排召回数（BM25/Dense 各召回 15 个候选）
            fuse_k=rc.fuse_k,                               # 按秩二次加权融合常数（10 + 名次作分母）
            rrf_weight=rc.rrf_weight,                       # 召回侧权重 0.6（稳定、托底）
            rerank_weight=rc.rerank_weight,                 # 精排侧权重 0.4（只做精度增益）
            metadata_filter=metadata_filter,                # 元数据硬过滤（如按 wiki_category 只看某类目）
            reject_threshold=rc.reject_threshold,           # 远程精排拒答阈值 0.40（最高分低于此 → 诚实拒答）
            heuristic_reject_threshold=rc.heuristic_reject_threshold,  # 启发式降级时的拒答阈值 0.25（分数尺度不同）
            rerank_granularity=rc.rerank_granularity,       # 精排粒度 parent=子块召回后对整卡全文打分
            rewrite_query=rewrite,                          # 查询改写结果（与原查询四路召回；改写失败回落原句）
            gate=build_gate(rc),                            # 置信度动态门控（enabled/min_score/min_margin/权重）
        )

    # ------------------------------------------------------------------ 问答

    def answer(self, query: str, top_k: Optional[int] = None,
               metadata_filter: Optional[Dict[str, Any]] = None,
               include_trace: bool = True) -> ChatResponse:
        """主问答入口：检索 → 拒答裁定 → 受约束生成 → 溯源角标 → 返回结构化响应。

        执行顺序（对应演示链路叙事）：
        1. 检索：调内核混合检索，得 final_results（子块）与链路快照数据；
        2. 拒答裁定（两级）：
           - 内核拒答（rejected）或无命中 → 直接拒答，**不调 LLM**；
           - 内核通过但远程精排最高分仍低于 reject_threshold → 服务层兜底拒答；
           - 若 rerank 降级为启发式打分（rerank_remote=False），仍按启发式阈值判定；
        3. 若通过：按父卡去重取整卡全文（parent_content）做 grounding 上下文，
           调 GroundingGenerator 生成答案（缓存 → 在线 → 离线兜底，绝不编造）；
        4. 角标对齐：解析正文 [来源: 卡片id - 章节名]，把变体 id 回正，标记到结构化
           Citation；同时识别"内核通过但 LLM 诚实拒答"的二次拒答（正文含拒答短语且无角标）；
        5. 返回 ChatResponse（answer / is_refused / citations / trace / latency_ms / notes）。

        Args:
            query: 用户问题。
            top_k: 最终命中条数；None 用配置 top_k。
            metadata_filter: 元数据硬过滤。
            include_trace: 是否返回链路快照 Trace（演示页可视化用；回归脚本传 False 省时）。

        Returns:
            ChatResponse。is_refused=True 时 answer 为诚实拒答文案，citations 为空；
            offline=True 时 answer 为离线兜底文案（仅返回检索片段）。
        """
        t0 = time.time()
        notes: List[str] = []
        rc = self.asm.cfg.retrieval

        res = self._search(query, top_k, metadata_filter)
        retrieval_ms = float(res.get("latency_ms", 0.0))
        final_results = res.get("final_results") or []

        top_score = max((_clamp_score(it.get("rerank_score")) for it in final_results), default=0.0)
        refused = bool(res.get("rejected")) or not final_results
        if (not refused and res.get("rerank_remote") and rc.reject_threshold is not None
                and top_score < rc.reject_threshold):
            refused = True   # 服务层兜底：远程精排成功但最高分仍低于阈值
        if res.get("rerank_remote") is False:
            notes.append("rerank 降级为启发式打分（网关不可用），内核按启发式阈值判定")

        llm_ms = 0.0

        # ---- 拒答：不调 LLM，直接返回 ----
        if refused:
            total_ms = round((time.time() - t0) * 1000, 2)
            return ChatResponse(
                query=query, answer=REFUSAL_TEXT, is_refused=True,
                refused_reason="LOW_CONFIDENCE", citations=[], offline=False,
                mode="refused", latency_ms=total_ms, notes=notes,
                trace=build_trace(res, retrieval_ms=retrieval_ms, llm_ms=0.0,
                                  total_ms=total_ms,
                                  reject_threshold=rc.reject_threshold) if include_trace else None,
            )

        # ---- grounding 上下文：按父卡去重，取整卡全文 ----
        contexts = self._build_contexts(final_results)
        citations = build_citations(final_results)

        # ---- LLM 生成（缓存 → 在线 → 离线兜底）----
        t_llm = time.time()
        answer_text = ""
        mode = "llm"
        offline = False
        try:
            answer_text = self.generator.generate(query, contexts)
            if self.generator.last_cached:
                mode = "cache"
                notes.append("答案来自预热缓存")
        except OfflineError as e:
            offline = True
            mode = "offline"
            answer_text = OFFLINE_TEXT
            notes.append(f"离线兜底：{e}")
        llm_ms = round((time.time() - t_llm) * 1000, 2)

        # ---- 内联角标对齐 + LLM 诚实拒答识别 ----
        if not offline and final_results and answer_text:
            # 角标 id 回正：把模型写出的变体卡片 id 归一化对齐到真实命中卡
            answer_text = canonicalize_answer_citations(
                answer_text, [c.card_id for c in citations])
        inline = parse_inline_citations(answer_text)
        if not offline:
            citations = build_citations(final_results, answer_text)
            if any(m in answer_text for m in REFUSAL_MARKERS) and not inline:
                total_ms = round((time.time() - t0) * 1000, 2)
                return ChatResponse(
                    query=query, answer=answer_text, is_refused=True,
                    refused_reason="NO_RELIABLE_KNOWLEDGE", citations=[], offline=False,
                    mode=mode, latency_ms=total_ms, notes=notes,
                    trace=build_trace(res, retrieval_ms=retrieval_ms, llm_ms=llm_ms,
                                      total_ms=total_ms,
                                      reject_threshold=rc.reject_threshold) if include_trace else None,
                )
            cited = {c.card_id for c in citations if c.cited_inline}
            known_norm = {_norm_id(c.card_id) for c in citations}
            uncited_inline = [cid for cid, _ in inline if _norm_id(cid) not in known_norm]
            if uncited_inline:
                notes.append(f"角标引用了未命中的卡片：{', '.join(sorted(set(uncited_inline)))}")
            if not cited:
                notes.append("答案未包含可识别的内联角标（结构化来源列表不受影响）")

        total_ms = round((time.time() - t0) * 1000, 2)
        return ChatResponse(
            query=query, answer=answer_text, is_refused=False, refused_reason=None,
            citations=citations, offline=offline, mode=mode,
            latency_ms=total_ms, notes=notes,
            trace=build_trace(res, retrieval_ms=retrieval_ms, llm_ms=llm_ms,
                              total_ms=total_ms,
                              reject_threshold=rc.reject_threshold) if include_trace else None,
        )

    @staticmethod
    def _build_contexts(final_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """把命中结果按父卡去重，拼成喂给 LLM 的 grounding 上下文列表。

        关键点：`rerank_granularity=parent` 时 `item["content"]` 仍是子块文本，
        整卡全文在 `metadata["parent_content"]` —— 必须取它，否则 LLM 只拿到半截卡。
        同一张卡命中多个子块时按 parent_id 去重，只喂一次整卡。

        Args:
            final_results: 内核 final_results 列表。

        Returns:
            每项 {card_id, title, version, status, source_file, content}，
            其中 content 为整卡全文（供 prompts.build_user_message 拼装）。
        """
        seen = set()
        contexts: List[Dict[str, str]] = []
        for it in final_results:
            md = it.get("metadata") or {}
            card_id = md.get("parent_id") or md.get("wiki_id") or ""
            if card_id in seen:
                continue
            seen.add(card_id)
            contexts.append({
                "card_id": card_id,
                "title": _collapse(md.get("Header_1") or md.get("wiki_title") or card_id),
                "version": str(md.get("wiki_version", "")),
                "status": str(md.get("wiki_status", "现行")),
                "source_file": md.get("source_file", ""),
                "content": md.get("parent_content") or it.get("content") or "",
            })
        return contexts

    # ------------------------------------------------------------------ 切片演示

    def chunk_demo(self, card_id: str) -> ChunkDemoResponse:
        """现场切一张 Wiki 卡，展示父子切片结构（演示"文件切片流程"的知识卡环节）。

        用 build_chunker(cfg) 工厂切卡——与索引构建、语料装载走同一实例化路径，
        保证"演示里看到的切片"与"实际入库的切片"完全一致（切片一致性）。

        Args:
            card_id: 卡片 id（即文件名去 .md，如 "ITKB-VPN-001"）。

        Returns:
            ChunkDemoResponse：父卡（整卡全文 + 长度）+ 子块列表
            （child_id / 所属 H2 小节 / 长度 / 是否含检索增强注入 / 预览）。

        Raises:
            FileNotFoundError: wiki_dir 下找不到该卡片。
        """
        path = self.asm.wiki_dir / f"{card_id}.md"
        if not path.exists():
            raise FileNotFoundError(f"未找到卡片：{card_id}")
        parent, children = self._chunker.split_wiki_document(str(path))
        kids = []
        for ch in children:
            md = ch.metadata or {}
            kids.append(ChunkChild(
                child_id=md.get("child_id", ""),
                section=md.get("Header_2", ""),
                length=len(ch.page_content),
                has_boost="【检索增强" in ch.page_content,
                preview=_collapse(ch.page_content)[:120],
                content=ch.page_content,
            ))
        return ChunkDemoResponse(
            card_id=card_id,
            title=str(parent.metadata.get("Header_1", card_id)),
            source_file=str(parent.metadata.get("source_file", path.name)),
            parent_length=len(parent.page_content),
            parent_preview=_collapse(parent.page_content)[:300],
            children=kids,
        )

    def list_cards(self) -> List[CardInfo]:
        """扫描 wiki 目录，返回全部卡片清单（供切片演示下拉与状态条统计）。

        用 WikiStructureAwareChunker.parse_wiki_frontmatter 解析各卡的 YAML frontmatter，
        提取 id / title / category / version；解析失败的卡片按文件名兜底。

        Returns:
            CardInfo 列表（按文件名排序，不含 _index.md）。
        """
        cards: List[CardInfo] = []
        for p in sorted(self.asm.wiki_dir.glob("*.md")):
            if p.name == "_index.md":
                continue
            try:
                meta, _ = WikiStructureAwareChunker.parse_wiki_frontmatter(
                    p.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
            cards.append(CardInfo(
                card_id=str(meta.get("id") or p.stem),
                title=str(meta.get("title") or p.stem),
                category=str(meta.get("category") or ""),
                version=str(meta.get("version") or ""),
            ))
        return cards

    # ------------------------------------------------------------------ 自检

    def health(self) -> HealthResponse:
        """服务自检：回显装配状态（指纹/切片数）+ 检索/生成可用性 + 缓存与卡片统计。

        Returns:
            HealthResponse。status 为 "UP"（wiki→Java 映射已加载）或 "DEGRADED"（映射缺失，
            不影响检索问答，仅表示未接生产 Java 侧的 articleId/versionId 映射）。
        """
        info = self.asm.health_info()
        try:
            cached = len(list(self.generator.cache_dir.glob("*.json")))
        except Exception:
            cached = 0
        return HealthResponse(
            status=info.status,
            chunk_count=info.chunk_count,
            wiki_fingerprint=info.wiki_fingerprint,
            config_fingerprint=info.config_fingerprint,
            rerank_available=info.rerank_available,
            rerank_provider=info.rerank_provider,
            llm_available=self.generator.available,
            llm_model=self.generator.model,
            offline=self.generator.offline_forced,
            cached_answers=cached,
            card_count=len(self.list_cards()),
        )
