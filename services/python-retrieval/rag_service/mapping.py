# -*- coding: utf-8 -*-
"""检索结果 -> 对外契约响应的字段映射（纯函数，无 IO，便于单测）。

修正点（相对"直传"的朴素实现）：
- chunkId 在 Chroma 持久化 metadata 中不存在，只有 child_id → 三级兜底
  child_id → chunk_id（内存 BM25 语料有）→ parent_id；
- rerank_granularity=parent 时 hybrid 返回的 item["content"] 仍是**子块文本**，
  整卡全文只在 metadata["parent_content"] → content 必须优先取 parent_content，
  否则下游拿到半截卡；
- articleId/versionId 来自 wiki→Java 映射表，缺失时降级为 wiki 侧取值
  （经 Java ④ MySQL 复核必被滤空，属预期的 DEGRADED 行为）。
"""

from typing import Any, Dict, Optional

from .contract import RagRetrievalResponse, RetrievedChunk

MAX_TITLE = 200      # 对齐 Java RagRetrievalService.titleOf
MAX_SNIPPET = 1000   # 对齐 Java snippetLength / 契约 citation.snippet.maxLength


def _clamp_score(value: Any) -> float:
    """rerank 原始分钳制到 [0,1] 并保留 4 位小数（契约要求 score ∈ [0,1]）。"""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(min(1.0, max(0.0, v)), 4)


def _collapse(text: Any) -> str:
    """压缩空白，对齐 Java snippetOf 的正则归一。"""
    return " ".join(str(text or "").split())


def _truncate_utf16(text: str, max_code_units: int) -> str:
    """按 UTF-16 编码单元长度截断（严密对齐 Java String.length() 限制与生僻字符/Emoji 场景）。"""
    if not text:
        return ""
    if len(text) <= max_code_units and all(ord(c) <= 0xFFFF for c in text):
        return text[:max_code_units]
    code_units = 0
    chars = []
    for c in text:
        cu = 2 if ord(c) > 0xFFFF else 1
        if code_units + cu > max_code_units:
            break
        code_units += cu
        chars.append(c)
    return "".join(chars)


def build_response(
    search_res: Dict[str, Any],
    *,
    wiki_mapping: Dict[str, Dict[str, Any]],
    request_category_id: Optional[str] = None,
    reject_threshold: Optional[float] = None,
    docstore: Optional[Any] = None,
    reasoning_res: Optional[Dict[str, Any]] = None,
) -> RagRetrievalResponse:
    """【链路二 · 步骤 5 契约响应装配与图谱注入】build_response(...)
    
    输入：
      - search_res: 主路混合检索精排结果字典；
      - wiki_mapping: 卡片 ID 与文章版本映射；
      - docstore: MySQL Docstore 实例；
      - reasoning_res: 图谱多跳推导上下文字典（包含 graph_facts 与 seed_entities）。
    动作：
      1. 组装标准化 RetrievedChunk 列表，补充 parent_content、版本号与归一化分值；
      2. 检查 reasoning_res：若存在图谱因果事实，格式化拓扑因果推导链为 graph_prefix，
         前置注入拼接至 Top-1 切片正文（top_item.content = graph_prefix + top_item.content）；
      3. 低置信度拒答门裁决（若 top_score < reject_threshold 则安全拒答）。
    返回：RagRetrievalResponse 对外标准检索契约响应。
    """
    final_results = search_res.get("final_results") or []
    rejected = bool(search_res.get("rejected", False))

    items = []
    for it in final_results:
        md = it.get("metadata") or {}
        pid = md.get("parent_id") or md.get("wiki_id")
        entry = wiki_mapping.get(pid) or {} if pid else {}

        content = it.get("parent_content") or md.get("parent_content")
        if not content and docstore and pid:
            content = docstore.get(pid)
        if not content:
            content = it.get("content") or ""
        version_id = entry.get("versionId") or md.get("wiki_version") or "unknown"
        article_id = entry.get("articleId") or pid or "unknown"
        title = _collapse(md.get("Header_1") or pid or "未命名知识片段") or "未命名知识片段"

        items.append(RetrievedChunk(
            chunk_id=md.get("child_id") or md.get("chunk_id") or md.get("parent_id") or "unknown",
            article_id=article_id,
            version_id=version_id,
            index_version=version_id,                     # 契约：indexVersion 恒等于 versionId
            title=title[:MAX_TITLE],
            snippet=_truncate_utf16(_collapse(content), MAX_SNIPPET) or title,
            content=content if content.strip() else title,   # 原样保留 Markdown 结构供下游拼 grounding
            category_id=request_category_id or entry.get("categoryId") or None,
            score=_clamp_score(it.get("rerank_score")),
        ))

    # 【链路二 · 步骤 5 图谱因果推导结论注入】
    # 当识别为复合多维故障且存在图谱事实时，将不可违背的刚性拓扑因果链前置注入至首条切片正文
    if reasoning_res and items:
        facts = reasoning_res.get("graph_facts") or []
        seeds = reasoning_res.get("seed_entities") or []
        if facts:
            top_facts_str = "\n".join(f"- {f}" for f in facts[:4])
            seeds_str = "、".join(seeds[:5])
            graph_prefix = (
                f"【知识图谱因果推导】\n"
                f"• 识别关联实体：{seeds_str}\n"
                f"• 拓扑因果推导链：\n{top_facts_str}\n"
                f"• 排查处置建议：建议优先顺延上述因果链处置根因节点。\n"
                f"---\n\n"
            )
            top_item = items[0]
            top_item.content = graph_prefix + top_item.content
            top_item.snippet = _truncate_utf16(_collapse(top_item.content), MAX_SNIPPET)

    top = max((i.score for i in items), default=0.0)
    if rejected or not items or (reject_threshold is not None and top < reject_threshold):
        return RagRetrievalResponse(
            items=[], domain="OFFICE_IT", suggested_reply_type="REFUSE",
            suggested_refusal_reason="LOW_CONFIDENCE", top_score=0.0,
            reliable=False, published_only=True,
        )

    return RagRetrievalResponse(
        items=items, domain="OFFICE_IT", suggested_reply_type="ANSWER",
        suggested_refusal_reason=None,
        top_score=top,                                    # 契约：topScore == max(items[].score)
        reliable=True, published_only=True,
    )
