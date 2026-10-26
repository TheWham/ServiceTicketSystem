# -*- coding: utf-8 -*-
"""输出门禁：数字守卫 + 单号守卫。

这是本链路相对既有链路的**唯一新增范式**，也是防幻觉的真正着力点。
`workflow_demo/rules.verify_citation` 守的是 `versionId`；本场景的幻觉对象是
**百分比与计数**（模型会把 9/28 写成"约 40%"），以及**编造的单号**。

两道守卫同构，都是"白名单 + 逐句剔除"：

  verify_numbers     回答里的每个百分比/计数必须能在 facts 里找到
  verify_ticket_ids  提到的每个单号必须能在本次样本白名单里找到

**只校验统计性数字**：`32%`、`9 单` 这类是结论，必须可溯源；而 `第一步`、
`机龄超过 5 年` 里的数字是叙述用语，校验它们会把正常表述误杀。
剔除到句子级 —— 一句话里有一个数字站不住，整句丢弃，不做局部改写。

剔除后若正文不足以支撑回答，调用方整体退回确定性模板（见 nodes._fallback_text）。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Set, Tuple

from .contract import AnalyticsFacts

# 统计性数字：百分数，或紧跟量词的技术计数
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_COUNT_RE = re.compile(r"(\d+)\s*(?:张|单|次|台|个|套|条|宗|起)")
_TICKET_RE = re.compile(r"\b[A-Z]{2,4}\d{8,}\b")

# 百分数容差（百分点）。给一点余量的原因：facts 里的占比保留一位小数，
# 模型转述成整数（32.1% → "约 32%"）是正常表述，不该判成编造。
# 但 32.1% 绝不能通过 "42%" —— 两者相差 9.9 个百分点，远超声明的容差。
_PERCENT_TOLERANCE = 0.5

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？；\n])")


def _allowed_ratios(facts: AnalyticsFacts) -> List[float]:
    ratios: List[float] = []
    for d in facts.dimensions:
        for e in d.entries:
            if e.ratio is not None:
                ratios.append(e.ratio)
            if e.ratio_of_all is not None:
                ratios.append(e.ratio_of_all)
    ratios.append(facts.coverage.ratio)
    return ratios


def _allowed_counts(facts: AnalyticsFacts) -> Set[int]:
    counts: Set[int] = set()
    for d in facts.dimensions:
        for e in d.entries:
            counts.add(e.count)
    counts.add(facts.coverage.labelled)
    counts.add(facts.coverage.total)
    counts.add(facts.coverage.window_total)
    # 被排除的非有效工单明细也要进白名单。**提示词要求模型披露"未覆盖部分"**，
    # 而这些数字就来自 facts.coverage.excluded —— 不放进白名单的话，模型照实披露
    # 反而会被门禁当成编造剔除（实测踩到过：整句"被排除的非有效工单为…10单、11单"
    # 被判为无法溯源）。要求披露却不许引用，是自相矛盾的。
    for value in (facts.coverage.excluded or {}).values():
        try:
            counts.add(int(value))
        except (TypeError, ValueError):
            continue
    for v in (facts.universe or {}).values():
        if isinstance(v, int):
            counts.add(v)
    for v in (facts.scope or {}).values():
        if isinstance(v, int):
            counts.add(v)
    # 代码算出的备件数量属于"系统结论"，必须可被正文引用 —— 否则模板里那句
    # 「预备 电源适配器 2 个（依据…6 单 × 0.3）」会被自己的门禁剔掉（实测踩到过：
    # 整句被判为无法溯源，答复里凭空少了两条备件建议）。
    # 只收 rule 来源：model 来源的建议已由 verify_suggestions 校验过。
    for r in facts.recommendations:
        if getattr(r, "source", "") == "rule" and getattr(r, "qty", 0) > 0:
            counts.add(int(r.qty))
    return counts


def _percent_ok(value: float, allowed: Sequence[float]) -> bool:
    return any(abs(value - a) <= _PERCENT_TOLERANCE for a in allowed)


def scan_numbers(text: str, facts: AnalyticsFacts) -> List[Tuple[str, str]]:
    """列出文本里所有站不住脚的统计数字，返回 `[(原文片段, 原因)]`。"""
    bad: List[Tuple[str, str]] = []
    allowed_pct = _allowed_ratios(facts)
    allowed_cnt = _allowed_counts(facts)

    for m in _PERCENT_RE.finditer(text):
        val = float(m.group(1))
        if not _percent_ok(val, allowed_pct):
            bad.append((m.group(0), f"占比 {m.group(0)} 不在本次统计结果中"))

    for m in _COUNT_RE.finditer(text):
        val = int(m.group(1))
        if val not in allowed_cnt:
            bad.append((m.group(0), f"计数 {m.group(0)} 不在本次统计结果中"))
    return bad


def scan_ticket_ids(text: str, facts: AnalyticsFacts) -> List[Tuple[str, str]]:
    """列出文本里编造的单号。"""
    allowed = facts.allowed_ticket_ids()
    return [(m.group(0), f"单号 {m.group(0)} 不在本次样本中")
            for m in _TICKET_RE.finditer(text) if m.group(0) not in allowed]


def _drop_sentences(text: str, offenders: Set[str]) -> Tuple[str, List[str]]:
    """把含有违规片段的句子整句丢弃。

    只丢句子、不做局部替换：把 "约 42%" 改成 "约 %" 会产出一句语法崩坏的话，
    还不如整句不要。丢到句子级也保证了剩下的话仍然自洽。
    """
    kept: List[str] = []
    dropped: List[str] = []
    for chunk in _SENTENCE_SPLIT.split(text or ""):
        if not chunk:
            continue
        if any(off in chunk for off in offenders):
            dropped.append(chunk.strip())
        else:
            kept.append(chunk)
    return "".join(kept).strip(), dropped


def verify_numbers(text: str, facts: AnalyticsFacts) -> Tuple[str, List[str], bool]:
    """过滤掉含未溯源数字的句子。返回 `(保留正文, 被剔除句子, 是否仍有内容)`。"""
    bad = scan_numbers(text, facts)
    if not bad:
        return text, [], bool((text or "").strip())
    kept, dropped = _drop_sentences(text, {frag for frag, _ in bad})
    return kept, dropped, bool(kept)


def verify_ticket_ids(text: str, facts: AnalyticsFacts) -> Tuple[str, List[str], bool]:
    """过滤掉含编造单号的句子。"""
    bad = scan_ticket_ids(text, facts)
    if not bad:
        return text, [], bool((text or "").strip())
    kept, dropped = _drop_sentences(text, {frag for frag, _ in bad})
    return kept, dropped, bool(kept)


def verify_all(text: str, facts: AnalyticsFacts) -> Tuple[str, List[str], bool]:
    """两道守卫串行。任一道把内容剔空，`ok=False` 由调用方降级。"""
    dropped: List[str] = []
    cur, d1, ok = verify_numbers(text, facts)
    dropped.extend(d1)
    if not ok:
        return "", dropped, False
    cur, d2, ok = verify_ticket_ids(cur, facts)
    dropped.extend(d2)
    return cur, dropped, ok


# ------------------------------------------------------------------ 建议守卫

def known_labels(facts: AnalyticsFacts) -> set:
    """facts 里**真实出现过**的全部标签（跨三个维度）。

    建议的依据只能落在这个集合里 —— 引用一个本次统计里不存在的标签，
    等于在产品建议里凭空引入了一条不存在的数据。
    """
    out = set()
    for d in facts.dimensions:
        for e in d.entries:
            out.add(e.label)
    return out


def verify_suggestions(suggestions: Sequence[Dict[str, Any]],
                       facts: AnalyticsFacts) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """逐条校验模型给出的建议。返回 `(保留的建议, [(被剔除的建议文本, 原因)])`。

    只管两件事，**不校验"外推方向本身"**：

      1. 依据标签必须真实存在于本次统计 —— 引用不存在的标签 = 凭空造数据；
      2. 建议正文里的数字/单号必须可溯源 —— 复用与他处同一套 `scan_*`。

    为什么不管方向：从「蓝屏 9 单」推出「建议排查内存与驱动一致性」是**归纳**，
    是这条链路存在的意义；把方向也管死，建议就只剩复述，没有价值了。
    红线只有一条 —— 不要出现数据里没有的东西。
    """
    labels = known_labels(facts)
    kept: List[Dict[str, Any]] = []
    dropped: List[Tuple[str, str]] = []

    for item in suggestions or []:
        text = str((item or {}).get("text") or "").strip()
        if not text:
            continue
        basis = [str(b).strip() for b in ((item or {}).get("basisLabels") or []) if str(b).strip()]

        unknown = [b for b in basis if b not in labels]
        if unknown:
            dropped.append((text, f"引用了本次统计里不存在的依据标签：{unknown}"))
            continue
        if not basis:
            # 无依据的建议 = 无法核对的建议。不剔它，就等于允许模型写一段
            # 与本次数据无关的话挂在统计结论下面。
            dropped.append((text, "未声明依据标签，无法核对是否基于本次统计"))
            continue

        bad = scan_numbers(text, facts) + scan_ticket_ids(text, facts)
        if bad:
            dropped.append((text, f"正文含不可溯源的内容：{[f for f, _ in bad][:2]}"))
            continue

        kept.append({"text": text, "basisLabels": basis})

    return kept, dropped