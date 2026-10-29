# -*- coding: utf-8 -*-
"""确定性聚合：占比、覆盖率、小样本闸门、备件决策表。

这是整条链路的**核心防线**，也是唯一产出数字的地方。模型碰不到本模块的任何中间量。

设计上的四个要点：

1. **双分母**：每条分布同时给 `ratio`（以该维度参与统计的工单数为分母）与
   `ratioOfAll`（以时间窗内全部工单数为分母）。"打印机故障占 42%"的自然读法是
   前者，"占本季度全部工单 18%"是后者 —— 口径不明是宏观归纳最常见的偷换。
2. **小样本只降级、不静默**：低于阈值的条目照常出现在结构里（调用方与前端能看到
   `count`），但 `ratio` 字段为 None，并在 `gates` 里留下可解释的原因。
3. **覆盖率必须披露**：把"没抽到标签"读成"没有发生"是宏观归纳最典型的系统性错误，
   所以覆盖率是 facts 的一等字段而不是附注。
4. **建议也是结论**：备件与巡检条目由决策表产出。让模型自由写采购建议，它就会
   编造型号、数量与巡检周期 —— 这是幻觉重灾区，不是创造性空间。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import yaml

from . import config as cfg
from . import taxonomy as tx
from .contract import (GATE_DEFAULT_WINDOW, GATE_LOW_COVERAGE, GATE_ROOT_CAUSE_UNAVAILABLE,
                       GATE_SMALL_SAMPLE, GATE_SMALL_UNIVERSE, SEVERITY_BLOCK, SEVERITY_INFO,
                       SEVERITY_WARN, SOURCE_RULE, AnalyticsFacts, Coverage, Dimension, Entry,
                       Gate, Recommendation, TicketRow)
from .timewindow import SOURCE_DEFAULT, Window

AXIS_ORDER = (tx.AXIS_SYMPTOM, tx.AXIS_DEVICE, tx.AXIS_ROOT_CAUSE)

# 每个条目的样例单号上限：下钻的价值在"可核验"，给太多反而淹没有效信息。
MAX_SAMPLE_IDS = 8

# 噪声原因的展示名：覆盖率披露要给员工看得懂的分类，而不是内部的枚举常量。
_EXCLUDED_LABELS = {
    tx.LOW_INFO_JUNK: "标题即测试串（test/123 之类）",
    tx.LOW_INFO_TEST: "联调/集成测试单",
    tx.LOW_INFO_IGNORE: "标题或描述标明「请忽略」",
    tx.LOW_INFO_EMPTY: "描述为空或过短",
}


def _pct(numerator: int, denominator: int) -> Optional[float]:
    """百分数，ROUND_HALF_UP 保留一位小数。

    刻意不用内置 `round()` —— 它是银行家舍入（ROUND_HALF_EVEN），`round(2.5) == 2`，
    在占比这类对外披露的数字上会造成"同样口径两次跑出不同结果"的困惑。
    """
    if denominator <= 0:
        return None
    q = Decimal(numerator) * 100 / Decimal(denominator)
    return float(q.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------- 备件建议（数字由代码算）

@dataclass(frozen=True)
class SparePartRule:
    """一条备件规则：某标签命中时，按 命中单量 × 系数 备货。"""

    axis: str
    label: str
    part: str
    unit: str
    factor: float


@dataclass(frozen=True)
class Policy:
    """`configs/analytics.yaml` 的内容。版本参与配置指纹 —— 系数一改，
    历史的备件建议就不可复现了（与词表同一条纪律）。"""

    version: str
    fingerprint: str
    spare_part_rules: Tuple[SparePartRule, ...]


def policy_fingerprint(path: Path) -> str:
    """策略配置的内容哈希（截 12 位）。与词表指纹同一条纪律 —— 系数一改，
    历史的备件建议就不可复现，指纹让"当时用的是哪一版"可追溯。"""
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def build_policy(data: Dict[str, Any], fingerprint: str) -> Policy:
    raw = data.get("spare_part_rules")
    if not isinstance(raw, list) or not raw:
        raise ValueError("spare_part_rules 不能为空 —— 没有它就没有任何备件建议")
    rules: List[SparePartRule] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError(f"备件规则必须是映射：{entry!r}")
        when = entry.get("when") or {}
        axis = str(when.get("axis") or "").strip()
        label = str(when.get("label") or "").strip()
        part = str(entry.get("part") or "").strip()
        unit = str(entry.get("unit") or "").strip()
        if not (axis and label and part and unit):
            raise ValueError(f"备件规则缺字段（when.axis/when.label/part/unit）：{entry!r}")
        try:
            factor = float(entry.get("factor"))
        except (TypeError, ValueError):
            raise ValueError(f"备件系数非法：{entry!r}") from None
        # 系数 > 1 意味着"每单备一件以上"，那已经不是备件系数而是消耗率，语义不同，
        # 评审时极易被当成笔误放过。这里直接拒，让它在加载期炸而不是在采购单上炸。
        if not 0 < factor <= 1:
            raise ValueError(f"备件系数应在 (0, 1]：{entry!r}")
        rules.append(SparePartRule(axis=axis, label=label, part=part, unit=unit, factor=factor))
    return Policy(version=str(data.get("version") or "unknown"),
                  fingerprint=fingerprint, spare_part_rules=tuple(rules))


_policy_cache: Dict[str, Policy] = {}


def load_policy(path: Optional[Path] = None, *, use_cache: bool = True) -> Policy:
    """加载备件策略。**缺失即失败**（不返回空策略）—— 没有备件规则就产不出任何
    备件建议，静默空转比启动期报错难查得多。"""
    target = Path(path) if path is not None else cfg.POLICY_PATH
    key = str(target)
    if use_cache and key in _policy_cache:
        return _policy_cache[key]
    if not target.exists():
        raise ValueError(f"策略配置不存在：{target}")
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"策略配置根节点必须是映射：{target}")
    pol = build_policy(data, policy_fingerprint(target))
    if use_cache:
        _policy_cache[key] = pol
    return pol


def _build_recommendations(entries_by_key: Dict[str, Entry], min_label_hits: int,
                           policy: Optional[Policy] = None) -> List[Recommendation]:
    """由配置里的备件规则产出建议。**备件数量的口径唯一真源在这里。**

    两条刻意的规则：

      · 命中量不足时**不给备件建议**，只留一条「说明」—— 依极少样本备货是浪费；
      · **同一备件名只保留第一条命中**。配置里 ROOT_CAUSE 规则排在 SYMPTOM 前面，
        因为备件是修根因用的；同名的现象兜底规则不会把它再算一遍。去重分母要覆盖
        「备件」与「说明」两种产出 —— 只对备件去重的话，同一个备件会既出建议又出说明。
    """
    pol = policy or load_policy()
    out: List[Recommendation] = []
    claimed_parts: Set[str] = set()

    for rule in pol.spare_part_rules:
        entry = entries_by_key.get(f"{rule.axis}:{rule.label}")
        if entry is None or entry.count <= 0:
            continue
        if rule.part in claimed_parts:
            continue
        claimed_parts.add(rule.part)

        if entry.count < min_label_hits:
            out.append(Recommendation(
                kind="说明",
                text=f"「{entry.label}」命中仅 {entry.count} 单，样本不足以据此安排备件",
                basis_label=entry.label, basis_count=entry.count,
                severity=SEVERITY_INFO, source=SOURCE_RULE))
            continue
        qty = max(1, math.ceil(entry.count * rule.factor))
        out.append(Recommendation(
            kind="备件",
            text=(f"预备 {rule.part} {qty} {rule.unit}"
                  f"（依据「{entry.label}」{entry.count} 单 × {rule.factor}）"),
            basis_label=entry.label, basis_count=entry.count,
            severity=SEVERITY_WARN, source=SOURCE_RULE, qty=qty))
    return out


# ------------------------------------------------------------------ 主入口

def build_facts(tickets: Sequence[TicketRow],
                window: Window,
                scope_domains: Sequence[tx.Domain] = (),
                taxonomy: Optional[tx.Taxonomy] = None,
                *,
                universe_total_hint: int = 0) -> AnalyticsFacts:
    """把投影扫描拿到的工单明细，算成可交给模型的 facts。

    `universe_total_hint`：当子域生效时，`tickets` 可能已经是子域过滤后的集合；
    传入未过滤的总数以计算 `ratioOfAll`（占全部工单的口径）。
    """
    tax = taxonomy or tx.load_taxonomy()
    min_universe = cfg.MIN_UNIVERSE
    min_denom = cfg.MIN_DENOM
    min_hits = cfg.MIN_LABEL_HITS
    min_coverage = cfg.MIN_COVERAGE_WARN

    excluded: Dict[str, int] = {}
    usable: List[TicketRow] = []
    extractions: Dict[str, tx.Extraction] = {}

    for t in tickets:
        reason = tx.low_information_reason(t.title, t.description)
        if reason:
            label = _EXCLUDED_LABELS.get(reason, reason)
            excluded[label] = excluded.get(label, 0) + 1
            continue
        ext = tx.extract_ticket(t.title, t.description, tax)
        # 根因只从解决方案文本抽取，**不从工单描述推断** —— 从描述猜根因正是幻觉来源
        if t.resolution:
            rc = tx.extract(t.resolution, tax)
            if rc.root_cause:
                ext.root_cause = rc.root_cause
                ext.hits.extend([h for h in rc.hits if h.axis == tx.AXIS_ROOT_CAUSE])
        usable.append(t)
        extractions[t.ticket_id] = ext

    universe_total = universe_total_hint or len(usable)

    # ---- 子域过滤（只在内存里做，见 taxonomy.DOMAIN 的说明）----
    scoped: List[TicketRow] = usable
    scope_info: Dict[str, Any] = {"domains": [], "applied": False, "count": len(usable)}
    domain_names = [d.name for d in scope_domains]
    if scope_domains:
        scoped = [t for t in usable
                  if any(d.matches(extractions[t.ticket_id].device,
                                   extractions[t.ticket_id].symptom)
                         for d in scope_domains)]
        scope_info = {"domains": domain_names, "applied": True, "count": len(scoped)}

    scoped_ids = {t.ticket_id for t in scoped}
    denominator = len(scoped)

    # ---- 三个维度的分布 ----
    dimensions: List[Dimension] = []
    entries_by_key: Dict[str, Entry] = {}
    for axis in AXIS_ORDER:
        counts: Dict[str, int] = {}
        samples: Dict[str, List[str]] = {}
        evidence: Dict[str, str] = {}
        labelled_count = 0
        for t in scoped:
            ext = extractions[t.ticket_id]
            label = getattr(ext, _attr_of(axis), None)
            if not label:
                continue
            labelled_count += 1
            counts[label] = counts.get(label, 0) + 1
            ids = samples.setdefault(label, [])
            if len(ids) < MAX_SAMPLE_IDS:
                ids.append(t.ticket_id)
            if label not in evidence:
                evidence[label] = ext.evidence_of(axis) or ""

        entries: List[Entry] = []
        for label, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            # 低于阈值 → 只给计数、不给占比。注意这里不抛异常、不删条目：
            # 条目本身有信息量，缺的是"能不能据此下结论"。
            below = count < min_hits or denominator < min_denom
            entry = Entry(label=label, count=count, denominator=denominator,
                          universe_total=universe_total, sample_ticket_ids=samples[label],
                          below_threshold=below, evidence=evidence.get(label, ""))
            entries.append(entry)
            entries_by_key[f"{axis}:{label}"] = entry

        unmatched = sum(1 for t in scoped if not getattr(extractions[t.ticket_id],
                                                         _attr_of(axis), None))
        dimensions.append(Dimension(axis=axis, entries=entries,
                                    other_count=labelled_count - sum(counts.values()),
                                    unmatched_count=unmatched))

    # ---- 覆盖率 ----
    labelled = sum(1 for t in scoped
                   if extractions[t.ticket_id].symptom or extractions[t.ticket_id].device)
    coverage = Coverage(
        labelled=labelled, total=denominator, window_total=universe_total, excluded=excluded,
        examples=[t.ticket_id for t in scoped if not extractions[t.ticket_id].symptom][:MAX_SAMPLE_IDS],
    )

    # ---- 闸门 ----
    gates: List[Gate] = []
    if universe_total < min_universe:
        gates.append(Gate(
            code=GATE_SMALL_UNIVERSE, severity=SEVERITY_BLOCK,
            message=f"时间窗内有效工单仅 {universe_total} 单（低于 {min_universe}），"
                    f"样本不足以做宏观归纳，只输出实际分布"))
    if scope_domains and denominator < min_denom:
        gates.append(Gate(
            code=GATE_SMALL_SAMPLE, severity=SEVERITY_WARN,
            message=f"限定范围「{'、'.join(domain_names)}」内有效工单 {denominator} 单"
                    f"（低于 {min_denom}），只给计数、不给占比"))
    if window.source == SOURCE_DEFAULT:
        gates.append(Gate(
            code=GATE_DEFAULT_WINDOW, severity=SEVERITY_WARN,
            message=f"提问未指明时间范围，按「{window.label}」统计，回答须声明该口径"))
    if coverage.ratio < min_coverage * 100 and denominator:
        gates.append(Gate(
            code=GATE_LOW_COVERAGE, severity=SEVERITY_WARN,
            message=f"标签覆盖率 {coverage.ratio}%（低于 {min_coverage * 100:.0f}%），"
                    f"结论仅供参考，须声明未覆盖部分"))
    root_dim = next((d for d in dimensions if d.axis == tx.AXIS_ROOT_CAUSE), None)
    if root_dim is not None and not root_dim.entries:
        gates.append(Gate(
            code=GATE_ROOT_CAUSE_UNAVAILABLE, severity=SEVERITY_WARN,
            message="工单未记录解决方案（ticket_resolution 为空），无法归纳根因，"
                    "以下仅为现象分布"))

    return AnalyticsFacts(
        window=window.as_dict(),
        scope=scope_info,
        universe={"total": universe_total, "scoped": denominator,
                  "labelled": labelled, "coverageRatio": coverage.ratio},
        coverage=coverage,
        dimensions=dimensions,
        recommendations=_build_recommendations(entries_by_key, min_hits),
        gates=gates,
    )


def _attr_of(axis: str) -> str:
    """轴 → Extraction 上的字段名。"""
    return {tx.AXIS_SYMPTOM: "symptom",
            tx.AXIS_DEVICE: "device",
            tx.AXIS_ROOT_CAUSE: "root_cause"}[axis]


def collect_unmatched(tickets: Sequence[TicketRow],
                      taxonomy: Optional[tx.Taxonomy] = None) -> List[Dict[str, Any]]:
    """回捞未命中任何症状标签的工单（噪声除外）。

    这是词表演化的**唯一原料**：没有这个桶，词表就只能在有人拍脑袋时才会更新。
    落盘后可由 `unmatched → 词频/聚类 → LLM 提候选标签 → 人工确认 → 入词表`
    的闭环消化掉。
    """
    tax = taxonomy or tx.load_taxonomy()
    out: List[Dict[str, Any]] = []
    for t in tickets:
        if tx.low_information_reason(t.title, t.description):
            continue
        ext = tx.extract_ticket(t.title, t.description, tax)
        if ext.symptom:
            continue
        out.append({
            "ticketId": t.ticket_id,
            "categoryId": t.category_id,
            "title": t.title,
            "excerpt": tx.strip_template(t.description)[:200],
            "device": ext.device,
        })
    return out