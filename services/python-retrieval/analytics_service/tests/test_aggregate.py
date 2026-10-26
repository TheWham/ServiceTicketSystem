# -*- coding: utf-8 -*-
"""确定性聚合的单测。

这一层产出的是要对主管披露的数字，而且**算错不会有任何报错** —— 只会安静地
给出一个错的占比。所以双分母、阈值、子域过滤、覆盖率逐条钉死。
"""

from __future__ import annotations

import pytest

from analytics_service import aggregate as agg
from analytics_service.contract import (GATE_DEFAULT_WINDOW, GATE_LOW_COVERAGE,
                                        GATE_ROOT_CAUSE_UNAVAILABLE, GATE_SMALL_SAMPLE,
                                        GATE_SMALL_UNIVERSE)
from analytics_service import config as cfg
from analytics_service import taxonomy as tx
from analytics_service.timewindow import parse_window

WINDOW = parse_window("本季度")


@pytest.fixture
def relaxed(monkeypatch):
    """放宽阈值，让迷你语料（11 张有效单）能跑出占比，用于验证计算本身。"""
    monkeypatch.setattr(cfg, "MIN_UNIVERSE", 5)
    monkeypatch.setattr(cfg, "MIN_DENOM", 3)
    monkeypatch.setattr(cfg, "MIN_LABEL_HITS", 2)


def _entry(facts, axis, label):
    for d in facts.dimensions:
        if d.axis != axis:
            continue
        for e in d.entries:
            if e.label == label:
                return e
    raise AssertionError(f"未找到条目 {axis}:{label}")


def _gate_codes(facts):
    return {g.code for g in facts.gates}


# ---------------------------------------------------------------- 基本口径

def test_噪声被剔除且分类计数(rows, taxonomy, relaxed):
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    assert facts.universe["total"] == 11, "13 张里应有 2 张噪声被剔除"
    assert facts.coverage.excluded.get("标题即测试串（test/123 之类）") == 1
    assert facts.coverage.excluded.get("标题或描述标明「请忽略」") == 1


def test_双分母同时给出(rows, taxonomy, relaxed):
    """『占本维度』与『占全部工单』是两种读法，缺一个就会被偷换口径。"""
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    e = _entry(facts, tx.AXIS_SYMPTOM, "蓝屏")
    assert e.count == 3
    assert e.denominator == 11
    assert e.universe_total == 11
    assert e.ratio == 27.3
    assert e.ratio_of_all == 27.3


def test_占比使用ROUND_HALF_UP(monkeypatch):
    """内置 round() 是银行家舍入，会让同样口径两次跑出不同结果。"""
    assert agg._pct(1, 8) == 12.5
    assert agg._pct(1, 16) == 6.3     # 6.25 → 6.3（round() 会给 6.2）
    assert agg._pct(3, 8) == 37.5


def test_分母为零时不给占比():
    assert agg._pct(1, 0) is None


# ---------------------------------------------------------------- 小样本闸门

def test_全库样本不足触发BLOCK闸门(rows, taxonomy, monkeypatch):
    monkeypatch.setattr(cfg, "MIN_UNIVERSE", 50)
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    assert GATE_SMALL_UNIVERSE in _gate_codes(facts)
    assert facts.has_block_gate() is True


def test_条目命中不足时只给计数不给占比(rows, taxonomy, relaxed):
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    e = _entry(facts, tx.AXIS_SYMPTOM, "VPN连接失败")
    assert e.count == 1
    assert e.below_threshold is True
    assert e.ratio is None and e.ratio_of_all is None
    # 条目本身仍在结构里：缺的是"能不能据此下结论"，不是这条数据没意义
    assert e.as_dict()["count"] == 1


def test_条目分母不足时同样降级(rows, taxonomy, monkeypatch):
    monkeypatch.setattr(cfg, "MIN_UNIVERSE", 5)
    monkeypatch.setattr(cfg, "MIN_DENOM", 50)
    monkeypatch.setattr(cfg, "MIN_LABEL_HITS", 1)
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    assert _entry(facts, tx.AXIS_SYMPTOM, "蓝屏").below_threshold is True


def test_未命中症状的工单计入unmatched(rows, taxonomy, relaxed):
    """投影仪那条不在词表里，必须落进 unmatched 桶而不是被静默忽略。"""
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    dim = next(d for d in facts.dimensions if d.axis == tx.AXIS_SYMPTOM)
    assert dim.unmatched_count == 1
    unmatched = agg.collect_unmatched(rows, taxonomy)
    assert [u["ticketId"] for u in unmatched] == ["TK202610010013"]


# ---------------------------------------------------------------- 子域

def test_子域过滤走词典而非分类(rows, taxonomy, relaxed):
    """打印机工单分类是 C_HW_PC；按 category 过滤会漏掉它。"""
    doms = tx.resolve_domains("网络与打印设备", taxonomy)
    facts = agg.build_facts(rows, WINDOW, doms, taxonomy=taxonomy)
    assert facts.scope["applied"] is True
    assert facts.scope["count"] == 3          # 打印机脱机 + 打印机卡纸 + VPN
    labels = [e.label for d in facts.dimensions if d.axis == tx.AXIS_SYMPTOM
              for e in d.entries]
    assert "打印机脱机" in labels and "打印机卡纸" in labels


def test_子域样本不足触发SMALL_SAMPLE但保留计数(rows, taxonomy, monkeypatch):
    monkeypatch.setattr(cfg, "MIN_UNIVERSE", 5)
    monkeypatch.setattr(cfg, "MIN_DENOM", 10)
    monkeypatch.setattr(cfg, "MIN_LABEL_HITS", 5)
    doms = tx.resolve_domains("网络与打印设备", taxonomy)
    facts = agg.build_facts(rows, WINDOW, doms, taxonomy=taxonomy)
    assert GATE_SMALL_SAMPLE in _gate_codes(facts)
    # 关键：不拒答，计数照给
    assert facts.universe["scoped"] == 3
    assert _entry(facts, tx.AXIS_SYMPTOM, "打印机脱机").count == 1


def test_未限定范围时scope为全量(rows, taxonomy, relaxed):
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    assert facts.scope["applied"] is False
    assert facts.scope["count"] == 11


# ---------------------------------------------------------------- 覆盖率

def test_覆盖率与排除明细一并披露(rows, taxonomy, relaxed):
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    assert facts.coverage.total == 11
    assert facts.coverage.labelled == 11
    assert facts.coverage.ratio == 100.0
    assert sum(facts.coverage.excluded.values()) == 2


def test_低覆盖率触发WARN闸门(rows, taxonomy, monkeypatch):
    """把"没抽到标签"读成"没有发生"是宏观归纳最典型的系统性错误。"""
    monkeypatch.setattr(cfg, "MIN_UNIVERSE", 5)
    monkeypatch.setattr(cfg, "MIN_DENOM", 3)
    monkeypatch.setattr(cfg, "MIN_LABEL_HITS", 2)
    monkeypatch.setattr(cfg, "MIN_COVERAGE_WARN", 2.0)   # 2.0 必然高于实际覆盖率
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    assert GATE_LOW_COVERAGE in _gate_codes(facts)


# ---------------------------------------------------------------- 根因维度

def test_根因只从resolution抽取(rows, taxonomy, relaxed):
    """从工单描述推断根因正是幻觉来源，必须只认解决方案文本。"""
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    e = _entry(facts, tx.AXIS_ROOT_CAUSE, "橡胶老化")
    assert e.count == 1
    assert e.sample_ticket_ids == ["TK202610010008"]


def test_根因无数据时挂不可归纳闸门(rows, taxonomy, relaxed):
    """去掉那条带 resolution 的工单后，根因维度必须如实声明不可归纳。"""
    stripped = [r for r in rows if r.ticket_id != "TK202610010008"]
    facts = agg.build_facts(stripped, WINDOW, taxonomy=taxonomy)
    assert GATE_ROOT_CAUSE_UNAVAILABLE in _gate_codes(facts)
    dim = next(d for d in facts.dimensions if d.axis == tx.AXIS_ROOT_CAUSE)
    assert dim.entries == []


# ---------------------------------------------------------------- 建议

def test_备件建议_样本不足时只给说明不给备件(rows, taxonomy, relaxed):
    """依极少样本备货是浪费 —— 低于 MIN_LABEL_HITS 时只说明，不产备件条目。

    迷你语料里「橡胶老化」只有 1 单，且它挂了进纸组件/搓纸轮这条备件规则。
    """
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    related = [r for r in facts.recommendations if r.basis_label == "橡胶老化"]
    assert related, "样本不足的标签仍应留下一条说明，否则读者不知道它被考虑过"
    assert all(r.kind == "说明" for r in related)
    assert all(r.source == "rule" for r in related)


def test_备件建议_按系数算出数量(rows, taxonomy, relaxed):
    """数量必须由代码算：命中单量 × 系数，可逐字复核。"""
    facts = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    related = [r for r in facts.recommendations if r.basis_label == "无法开机/电源无反应"]
    assert related, "命中 2 单达到阈值，应产出备件条目"
    assert all(r.kind == "备件" for r in related)
    # 2 单 × 0.3 = 0.6 → 向上取整 1
    assert any("× 0.3" in r.text for r in related)
    assert any("电源适配器 1 个" in r.text for r in related)


def test_备件建议_同名备件只出现一次(rows, taxonomy, relaxed):
    """备件是修根因用的：ROOT_CAUSE 规则优先，同名的现象兜底规则不再算一遍。

    否则「电源适配器」会被现象（无法开机）与根因（电源故障）各算一次，
    读者会以为要备两份。
    """
    from analytics_service.aggregate import SparePartRule, Policy, _build_recommendations

    entries = {}
    for r in agg.build_facts(rows, WINDOW, taxonomy=taxonomy).dimensions:
        for e in r.entries:
            entries[f"{r.axis}:{e.label}"] = e

    pol = Policy(version="t", fingerprint="x", spare_part_rules=(
        SparePartRule("ROOT_CAUSE", "橡胶老化", "同一件", "套", 0.5),
        SparePartRule("SYMPTOM", "打印机脱机", "同一件", "套", 0.9),
    ))
    out = _build_recommendations(entries, min_label_hits=1, policy=pol)
    assert len(out) == 1, [r.text for r in out]
    # 保留的是排在前面的根因规则（0.5），不是现象兜底（0.9）
    assert "0.5" in out[0].text


def test_建议条目集合与模型无关(rows, taxonomy, relaxed):
    """同一批数据跑两次，建议条目必须逐字一致。"""
    a = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    b = agg.build_facts(rows, WINDOW, taxonomy=taxonomy)
    assert [r.as_dict() for r in a.recommendations] == [r.as_dict() for r in b.recommendations]


# ---------------------------------------------------------------- 备件策略配置

def test_策略配置可加载(taxonomy):
    pol = agg.load_policy(use_cache=False)
    assert pol.version
    assert len(pol.fingerprint) == 12
    assert pol.spare_part_rules, "没有备件规则就产不出任何备件建议"


def test_策略系数超一被拒():
    """系数 > 1 意味着"每单备一件以上"，那是消耗率不是备件系数 —— 加载期拒掉，
    别让它在采购单上炸。"""
    import pytest as _pytest
    with _pytest.raises(ValueError, match="备件系数应在"):
        agg.build_policy({"spare_part_rules": [
            {"when": {"axis": "SYMPTOM", "label": "X"}, "part": "p", "unit": "个", "factor": 1.5}
        ]}, "fp")


def test_策略缺字段被拒():
    import pytest as _pytest
    with _pytest.raises(ValueError, match="缺字段"):
        agg.build_policy({"spare_part_rules": [
            {"when": {"axis": "SYMPTOM", "label": "X"}, "part": "p"}
        ]}, "fp")


def test_策略指纹随内容变化(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text("version: '1'\nspare_part_rules:\n- {when: {axis: S, label: L}, part: p, unit: u, factor: 0.5}\n",
                 encoding="utf-8")
    f1 = agg.policy_fingerprint(p)
    p.write_text("version: '1'\nspare_part_rules:\n- {when: {axis: S, label: L}, part: p, unit: u, factor: 0.7}\n",
                 encoding="utf-8")
    assert agg.policy_fingerprint(p) != f1, "系数改了指纹必须变，否则历史建议不可追溯"


# ---------------------------------------------------------------- 默认口径闸门

def test_默认时间窗会挂声明闸门(rows, taxonomy, relaxed):
    facts = agg.build_facts(rows, parse_window("统计各类故障"), taxonomy=taxonomy)
    assert GATE_DEFAULT_WINDOW in _gate_codes(facts)