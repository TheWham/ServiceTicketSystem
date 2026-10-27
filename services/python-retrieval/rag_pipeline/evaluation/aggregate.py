# -*- coding: utf-8 -*-
"""跨工单聚合归纳评测：与单卡命中口径**完全正交**的一套指标。

为什么必须另起一套，而不是给 `GoldenSetEvaluator` 加分支：后者的命中判定是
「取召回结果里第一个匹配 `expected_chunks` 的卡、记其 rank、break」——那是**单卡命中**
口径，而聚合题压根没有"该命中哪一张卡"这回事，它要评的是"跨一批记录的归纳是否正确
且可核验"。把两类塞进一个类，会把"检索质量"与"聚合正确性"两个正交指标耦在一起，
日后无法单独调参。

`GoldenSetEvaluator` 的 `__init__` 还绑死了 `retriever`，而聚合链路**没有 retriever**
（走确定性聚合、不走向量检索）—— 所以这里从零写，只复用报告渲染风格。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# 门槛：聚合是确定性链路，正确性不容错，所以多数指标要求 100%。
THRESHOLDS = {
    "aggregate_pass_rate": 100.0,
    "number_fidelity_rate": 100.0,
    "drilldown_coverage": 90.0,
    "small_sample_guard_rate": 100.0,
    "coverage_disclosure_rate": 100.0,
    "taxonomy_coverage_rate": 80.0,
    # 误杀哨兵：作答类题目里**没有任何数字/建议被门禁剔除**的比例。
    #
    # 为什么需要它：`number_fidelity_rate` 复核的是**最终正文**——门禁已经剔过一遍，
    # 所以它抓不到"误杀"。实测踩到过：提示词要求模型披露被排除的工单明细，
    # 而门禁白名单里没有那些数字，模型照实披露反被整句剔除，两个指标看起来都正常。
    # 这条指标就是为那类"要求披露却不许引用"的自相矛盾准备的。
    "guard_clean_rate": 100.0,
}


def _find_dimension(facts: Dict[str, Any], axis: str) -> Optional[Dict[str, Any]]:
    for dim in (facts or {}).get("dimensions") or []:
        if dim.get("axis") == axis:
            return dim
    return None


def _entries(facts: Dict[str, Any], axis: str) -> List[Dict[str, Any]]:
    dim = _find_dimension(facts, axis)
    return list(dim.get("entries") or []) if dim else []


def _gate_codes(facts: Dict[str, Any]) -> set:
    return {g.get("code") for g in (facts or {}).get("gates") or []}


class AggregateSetEvaluator:
    """跑一遍聚合题，按 `aggregate_expect` 逐题校验。"""

    def __init__(self, dataset_path: str):
        raw = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
        self.dataset: List[Dict[str, Any]] = [e for e in raw if e.get("is_aggregate_check")]
        if not self.dataset:
            raise ValueError(f"数据集中没有聚合题（is_aggregate_check=true）：{dataset_path}")

    # ---------------------------------------------------------------- 单题校验

    def _check(self, item: Dict[str, Any], result: Dict[str, Any]) -> List[str]:
        """返回失败原因列表；空列表 = 通过。"""
        expect = item.get("aggregate_expect") or {}
        failures: List[str] = []
        facts = result.get("analyticsFacts") or {}

        # ---- 路由类期望 ----
        if expect.get("expect_not_analytics"):
            if result.get("intent") != "NOT_ANALYTICS":
                failures.append(f"应判为 NOT_ANALYTICS，实际 {result.get('intent')}")
            if facts:
                failures.append("非分析型请求不应产生统计结果")
            return failures

        if expect.get("expect_role_denied"):
            if result.get("replyType") != "REFUSE" or result.get("refusalReason") != "POLICY_BLOCKED":
                failures.append(f"越权应被拒答，实际 {result.get('refusalReason')}")
            if facts:
                failures.append("越权请求不应取数或产生统计结果")
            return failures

        # ---- 以下都要求真的跑通了聚合 ----
        if not facts:
            return [f"未产生统计结果（verdict={result.get('verdict')}, "
                    f"refusal={result.get('refusalReason')}）"]

        axis = expect.get("dimension")
        labels = [e.get("label") for e in _entries(facts, axis)] if axis else []

        if expect.get("expect_empty_dimension"):
            if _entries(facts, expect["expect_empty_dimension"]):
                failures.append(f"{expect['expect_empty_dimension']} 应无条目（无来源可归纳）")

        for label in expect.get("expected_labels") or []:
            if label not in labels:
                failures.append(f"缺少期望标签「{label}」")
        for label in expect.get("forbid_labels") or []:
            if label in labels:
                failures.append(f"出现了禁止标签「{label}」")

        top1 = expect.get("expected_top1")
        if top1 and (not labels or labels[0] != top1):
            failures.append(f"Top-1 应为「{top1}」，实际「{labels[0] if labels else '无'}」")

        # 并列时的 Top-1：命中数相同、排序按标签名裁决，把名次钉死会让评测变成
        # 在考验排序实现而不是聚合正确性。所以这类题给一个可接受集合。
        top1_any = expect.get("expected_top1_any")
        if top1_any and (not labels or labels[0] not in top1_any):
            failures.append(f"Top-1 应为 {top1_any} 之一，实际「{labels[0] if labels else '无'}」")

        # 占比与计数：口径错一位就会被这里挡住（比"标签对了"强得多的断言）
        tol = float(expect.get("ratio_tolerance") or 0.5)
        for label, want in (expect.get("expected_ratios") or {}).items():
            entry = next((e for e in _entries(facts, axis) if e.get("label") == label), None)
            got = None if entry is None else entry.get("ratio")
            if got is None:
                failures.append(f"「{label}」应给出占比 {want}%，实际未给出")
            elif abs(float(got) - float(want)) > tol:
                failures.append(f"「{label}」占比应 {want}%±{tol}，实际 {got}%")

        for label, want in (expect.get("expected_counts") or {}).items():
            if label == "total":
                got = (facts.get("universe") or {}).get("total")
                if got != want:
                    failures.append(f"有效工单数应 {want}，实际 {got}")
                continue
            if label == "raw":
                continue      # raw 是时间窗内原始张数，不在 facts 里，由 ground_truth 记录
            entry = next((e for e in _entries(facts, axis) if e.get("label") == label), None)
            if entry is None or entry.get("count") != want:
                failures.append(f"「{label}」计数应 {want}，实际 "
                                f"{entry.get('count') if entry else '无'}")

        # ---- 闸门 ----
        codes = _gate_codes(facts)
        for code in expect.get("expect_gates") or []:
            if code not in codes:
                failures.append(f"缺少期望闸门 {code}")
        # 反向断言：某些闸门**出现**就说明这道题的前提已经不成立
        # （如 ROOT_CAUSE_UNAVAILABLE 表示根因维度无来源，此时不该再断言能归纳出根因）
        for code in expect.get("forbid_gates") or []:
            if code in codes:
                failures.append(f"出现了不该有的闸门 {code}")

        if expect.get("expect_no_ratio"):
            bad = [e.get("label") for e in _entries(facts, axis)
                   if e.get("ratio") is not None]
            if bad:
                failures.append(f"样本不足时不得给占比，但 {bad} 给了")

        # ---- 口径与范围 ----
        scope = expect.get("expect_scope")
        if scope:
            got = (facts.get("scope") or {}).get("domains") or []
            if list(got) != list(scope):
                failures.append(f"范围限定应为 {scope}，实际 {got}")

        if expect.get("expect_default_window"):
            win = facts.get("window") or {}
            if win.get("source") != "默认最近90天":
                failures.append(f"未指定时间范围时应走默认口径，实际 {win.get('source')}")

        if expect.get("expect_coverage_disclosure"):
            cov = facts.get("coverage") or {}
            text = result.get("answerText") or ""
            marker = str(cov.get("ratio"))
            if "覆盖率" not in text and marker not in text:
                failures.append("回答未披露标签覆盖率")

        if expect.get("require_drilldown"):
            missing = [e.get("label") for e in _entries(facts, axis)
                       if e.get("count", 0) > 0 and not e.get("sampleTicketIds")]
            if missing:
                failures.append(f"条目缺少可下钻样例单号：{missing}")

        return failures

    # ---------------------------------------------------------------- 主入口

    def run_evaluation(self, ds: Any = None, role: str = "ENGINEER",
                       model: Any = None) -> Dict[str, Any]:
        """跑全部聚合题。`ds` 为空时按运行时身份走真实投影扫描接口。"""
        from analytics_service.engine import AnalyticsWorkflow

        workflow = AnalyticsWorkflow(ds=ds, model=model)
        rows: List[Dict[str, Any]] = []

        for item in self.dataset:
            expect = item.get("aggregate_expect") or {}
            run_role = expect.get("run_role") or role
            result = workflow.run(item["query"], role=run_role)
            failures = self._check(item, result)
            facts = result.get("analyticsFacts") or {}
            rows.append({
                "id": item["id"],
                "query": item["query"],
                "role": run_role,
                "intent": result.get("intent"),
                "replyType": result.get("replyType"),
                "passed": not failures,
                "failures": failures,
                "facts": result.get("analyticsFacts"),
                "answerText": result.get("answerText"),
                # 评测侧复用的两个派生字段：闸门期望 vs 实测，供守卫类指标比对
                "expectGates": list(expect.get("expect_gates") or []),
                "gateCodes": [g.get("code") for g in (facts.get("gates") or [])],
                # 门禁行为留痕：guard_clean_rate 靠它判断有没有"误杀"
                "findingCodes": [f.get("code") for f in (result.get("findings") or [])],
            })

        summary = self._summarize(rows)
        summary["rows"] = rows
        self._print_console_dashboard(summary)
        return summary

    # ---------------------------------------------------------------- 指标

    def _summarize(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(rows)
        passed = sum(1 for r in rows if r["passed"])

        # number_fidelity：回答里每个百分比/计数都必须能溯源。
        # 注意这条不是"再过一遍门禁"——门禁已在链路里跑过，这里是在**评测侧独立复核**，
        # 防止门禁被误改后链路与评测同时失灵还显示通过。
        from analytics_service import rules
        fidelity_checked = fidelity_ok = 0
        for r in rows:
            facts = r.get("facts")
            text = r.get("answerText") or ""
            if not facts or not text:
                continue
            obj = _facts_to_object(facts)
            bad = rules.scan_numbers(text, obj) + rules.scan_ticket_ids(text, obj)
            fidelity_checked += 1
            if not bad:
                fidelity_ok += 1

        # drilldown_coverage：所有条目里带样例单号的比例
        entries_all = entries_drill = 0
        for r in rows:
            for dim in (r.get("facts") or {}).get("dimensions") or []:
                for e in dim.get("entries") or []:
                    if e.get("count", 0) <= 0:
                        continue
                    entries_all += 1
                    if e.get("sampleTicketIds"):
                        entries_drill += 1

        # small_sample_guard：**期望**触发小样本闸门的题里，实际挂上了几道。
        # 分母是"期望"而不是"实际"—— 用实际当分母的话这个指标恒为 100%，
        # 一条闸门失效的回归会被它完全掩盖。
        guard_expected = [r for r in rows
                          if {"SMALL_SAMPLE", "SMALL_UNIVERSE"} & set(r.get("expectGates") or [])]
        guard_ok = sum(1 for r in guard_expected
                       if {"SMALL_SAMPLE", "SMALL_UNIVERSE"} & set(r.get("gateCodes") or []))

        # coverage_disclosure：作答类题目里披露了覆盖率的比例
        answered = [r for r in rows if r.get("facts") and r.get("replyType") == "ANSWER"]
        disclosed = sum(1 for r in answered
                        if "覆盖率" in (r.get("answerText") or "")
                        or str(((r["facts"].get("coverage") or {}).get("ratio"))) in
                        (r.get("answerText") or ""))

        # taxonomy_coverage_rate：词表对工单的覆盖率（取最后一题的口径做代表）
        tax_cov = None
        for r in reversed(rows):
            cov = (r.get("facts") or {}).get("coverage")
            if cov:
                tax_cov = cov.get("ratio")
                break

        # guard_clean_rate：作答类题目里没有任何剔除记录的比例。
        # 剔除本身不一定是错（模型真编了就该剔），但在评测里它大多意味着
        # **门禁与提示词口径打架** —— 那类问题不会让任何其他指标掉下来。
        guard_codes = {"CLAIM_REJECTED", "SUGGESTION_REJECTED", "NARRATIVE_FALLBACK"}
        guard_pool = [r for r in rows if r.get("facts") and r.get("replyType") == "ANSWER"]
        guard_clean = sum(1 for r in guard_pool
                          if not (guard_codes & set(r.get("findingCodes") or [])))

        return {
            "total": total,
            "passed": passed,
            "aggregate_pass_rate": _pct(passed, total),
            "number_fidelity_rate": _pct(fidelity_ok, fidelity_checked),
            "drilldown_coverage": _pct(entries_drill, entries_all),
            "small_sample_guard_rate": _pct(guard_ok, len(guard_expected)) if guard_expected else 100.0,
            "coverage_disclosure_rate": _pct(disclosed, len(answered)),
            "taxonomy_coverage_rate": tax_cov if tax_cov is not None else 0.0,
            "guard_clean_rate": _pct(guard_clean, len(guard_pool)) if guard_pool else 100.0,
        }

    def _print_console_dashboard(self, summary: Dict[str, Any]) -> None:
        print("\n" + "=" * 78)
        print(f"🚀 跨工单聚合归纳评测（{summary['total']} 题，通过 {summary['passed']}）")
        print("=" * 78)
        for key, threshold in THRESHOLDS.items():
            value = summary.get(key)
            mark = "✅" if value is not None and value >= threshold else "⚠️"
            print(f"  {mark} {key:<28} {value:>6}%   （门槛 ≥ {threshold}%）")
        for row in summary["rows"]:
            flag = "✅" if row["passed"] else "❌"
            print(f"\n  {flag} [{row['id']}] {row['query'][:52]}")
            for f in row["failures"]:
                print(f"        · {f}")

    def generate_markdown_report(self, path: Path, summary: Dict[str, Any]) -> None:
        lines = [
            "# 跨工单聚合归纳评测报告",
            "",
            f"> 聚合题 {summary['total']} 道，通过 {summary['passed']} 道",
            "",
            "## 一、指标大盘",
            "",
            "| 指标 | 门槛 | 实测 | 判定 |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for key, threshold in THRESHOLDS.items():
            value = summary.get(key)
            ok = value is not None and value >= threshold
            lines.append(f"| `{key}` | ≥ {threshold}% | **{value}%** | {'✅ 达标' if ok else '⚠️ 需调优'} |")
        lines += ["", "## 二、逐题结果", ""]
        for row in summary["rows"]:
            lines.append(f"### [{'通过' if row['passed'] else '未通过'}] {row['id']}")
            lines.append(f"- **提问**：`{row['query']}`")
            lines.append(f"- **意图 / 回复类型**：{row['intent']} / {row['replyType']}")
            if row["failures"]:
                lines.append("- **失败原因**：")
                for f in row["failures"]:
                    lines.append(f"  - {f}")
            lines.append("")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")


def _facts_to_object(facts: Dict[str, Any]) -> Any:
    """把回传的 facts dict 还原成门禁用的对象，好在评测侧独立复核一遍。"""
    from analytics_service.contract import (AnalyticsFacts, Coverage, Dimension, Entry,
                                            Gate, Recommendation)

    cov_raw = facts.get("coverage") or {}
    coverage = Coverage(labelled=cov_raw.get("labelled", 0), total=cov_raw.get("total", 0),
                        window_total=cov_raw.get("windowTotal", 0),
                        excluded=cov_raw.get("excluded") or {},
                        examples=cov_raw.get("examples") or [])
    dims = []
    for d in facts.get("dimensions") or []:
        entries = []
        for e in d.get("entries") or []:
            entry = Entry(label=e.get("label", ""), count=e.get("count", 0),
                          denominator=e.get("denominator", 0),
                          universe_total=(facts.get("universe") or {}).get("total", 0),
                          sample_ticket_ids=e.get("sampleTicketIds") or [],
                          below_threshold=bool(e.get("belowThreshold")))
            entries.append(entry)
        dims.append(Dimension(axis=d.get("axis", ""), entries=entries,
                              other_count=d.get("otherCount", 0),
                              unmatched_count=d.get("unmatchedCount", 0)))
    gates = [Gate(code=g.get("code", ""), severity=g.get("severity", ""),
                  message=g.get("message", "")) for g in facts.get("gates") or []]
    return AnalyticsFacts(window=facts.get("window") or {}, scope=facts.get("scope") or {},
                          universe=facts.get("universe") or {}, coverage=coverage,
                          dimensions=dims,
                          recommendations=[Recommendation(kind=r.get("kind", ""),
                                                          text=r.get("text", ""),
                                                          basis_label=r.get("basisLabel", ""),
                                                          basis_count=r.get("basisCount", 0),
                                                          source=r.get("source", "rule"),
                                                          qty=r.get("qty", 0) or 0)
                                           for r in facts.get("recommendations") or []],
                          gates=gates)


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator * 100.0 / denominator, 1) if denominator else 100.0