# -*- coding: utf-8 -*-
"""输出门禁的单测：数字守卫 + 单号守卫。

这是防幻觉的真正着力点，也是最容易"看起来在防、实际上放过去"的一环 ——
所以既要有"该拦的拦住"，也要有"不该拦的别误杀"。
"""

from __future__ import annotations

import pytest

from analytics_service import aggregate as agg
from analytics_service import config as cfg
from analytics_service import rules
from analytics_service.timewindow import parse_window

WINDOW = parse_window("本季度")


@pytest.fixture
def facts(rows, taxonomy, monkeypatch):
    monkeypatch.setattr(cfg, "MIN_UNIVERSE", 5)
    monkeypatch.setattr(cfg, "MIN_DENOM", 3)
    monkeypatch.setattr(cfg, "MIN_LABEL_HITS", 2)
    return agg.build_facts(rows, WINDOW, taxonomy=taxonomy)


# ---------------------------------------------------------------- 数字守卫

def test_合法占比与计数通过(facts):
    text = "本季度蓝屏 3 单，占 27.3%。"
    kept, dropped, ok = rules.verify_numbers(text, facts)
    assert ok is True and dropped == [] and kept == text


def test_编造占比被剔除(facts):
    text = "蓝屏占比高达 42%。"
    kept, dropped, ok = rules.verify_numbers(text, facts)
    assert ok is False
    assert dropped and "42%" in dropped[0]


def test_编造计数被剔除(facts):
    text = "本季度共发生 99 单蓝屏。"
    _, dropped, ok = rules.verify_numbers(text, facts)
    assert ok is False and dropped


def test_占比容差允许整数化转述(facts):
    """facts 里是 27.3%，模型写成"约 27%"是正常表述，不该判成编造。"""
    kept, dropped, ok = rules.verify_numbers("约占 27%", facts)
    assert ok is True and dropped == []


def test_容差不放过真正的编造(facts):
    """27.3% 绝不能通过 42% —— 相差 14.7 个百分点，远超声明的 0.5。"""
    _, dropped, ok = rules.verify_numbers("占比 42%", facts)
    assert ok is False and dropped


def test_非统计数字不被误杀(facts):
    """"第一步"、"机龄超过 5 年"是叙述用语，校验它们会把正常表述误杀。"""
    text = "第一步先看覆盖率；对机龄超过 5 年的设备优先巡检。"
    kept, dropped, ok = rules.verify_numbers(text, facts)
    assert ok is True and dropped == []


def test_被排除明细的数字可溯源(facts):
    """提示词要求模型披露「未覆盖部分」，而这些数字来自 coverage.excluded。

    不把它们放进白名单，模型**照实披露**反而会被门禁当成编造剔除 ——
    实测踩到过：整句「被排除的非有效工单为…10单、11单」被判为无法溯源。
    要求披露却不许引用，是自相矛盾的。
    """
    excluded = facts.coverage.excluded
    assert excluded, "迷你语料应有被排除的工单"
    n = next(iter(excluded.values()))
    kept, dropped, ok = rules.verify_numbers(f"被排除的非有效工单共 {n} 单。", facts)
    assert ok is True and dropped == []


def test_整句剔除而不是局部改写(facts):
    """把 "约 42%" 改成 "约 %" 会产出语法崩坏的话，不如整句不要。"""
    text = "蓝屏 3 单。蓝屏占比 42%。无法开机 2 单。"
    kept, dropped, ok = rules.verify_numbers(text, facts)
    assert ok is True
    assert "42%" not in kept
    assert "蓝屏 3 单" in kept and "无法开机 2 单" in kept
    assert len(dropped) == 1


def test_剔空后判定为不可用(facts):
    _, dropped, ok = rules.verify_numbers("占比 42%。", facts)
    assert ok is False and dropped


# ---------------------------------------------------------------- 单号守卫

def test_白名单内的单号通过(facts):
    text = "详见 TK202610010002。"
    kept, dropped, ok = rules.verify_ticket_ids(text, facts)
    assert ok is True and dropped == []


def test_编造的单号被剔除(facts):
    text = "详见 TK202609300999。"
    _, dropped, ok = rules.verify_ticket_ids(text, facts)
    assert ok is False and dropped


def test_非单号格式的数字串不触发单号守卫(facts):
    text = "型号 ABC123 的电源适配器。"
    _, dropped, ok = rules.verify_ticket_ids(text, facts)
    assert ok is True and dropped == []


# ---------------------------------------------------------------- 串行组合

def test_两道守卫串行且任一失败即不可用(facts):
    assert rules.verify_all("蓝屏 3 单，见 TK202610010002。", facts)[2] is True
    assert rules.verify_all("占比 42%。", facts)[2] is False
    assert rules.verify_all("见 TK202609300999。", facts)[2] is False


def test_白名单来自facts而非全局(facts):
    """单号白名单必须是本次样本 —— 否则模型能引用任意历史单号。"""
    allowed = facts.allowed_ticket_ids()
    assert "TK202610010002" in allowed
    assert "TK202609300999" not in allowed


# ---------------------------------------------------------------- 建议守卫

def test_建议_依据标签存在则放行(facts):
    kept, dropped = rules.verify_suggestions(
        [{"text": "对蓝屏集中的机型做内存与驱动一致性排查", "basisLabels": ["蓝屏"]}], facts)
    assert len(kept) == 1 and dropped == []


def test_建议_引用不存在的标签被剔除(facts):
    """引用本次统计里没有的标签 = 凭空引入一条不存在的数据。"""
    kept, dropped = rules.verify_suggestions(
        [{"text": "针对主板故障做专项排查", "basisLabels": ["主板故障"]}], facts)
    assert kept == []
    assert dropped and "不存在" in dropped[0][1]


def test_建议_未声明依据被剔除(facts):
    """无依据的建议 = 无法核对的建议，不能挂在统计结论下面。"""
    kept, dropped = rules.verify_suggestions(
        [{"text": "建议加强日常巡检力度", "basisLabels": []}], facts)
    assert kept == []
    assert dropped and "未声明依据" in dropped[0][1]


def test_建议_正文含不可溯源数字被剔除(facts):
    facts_obj = facts
    kept, dropped = rules.verify_suggestions(
        [{"text": "建议把巡检频次提高到每月 5 次", "basisLabels": ["蓝屏"]}], facts_obj)
    assert kept == []
    assert dropped and "不可溯源" in dropped[0][1]


def test_建议_允许合理外推方向(facts):
    """守卫只管"别造数、别引用不存在的标签"，不管推断方向本身 ——

    从「蓝屏 3 单」推出"先查内存与驱动一致性"是归纳，是这条链路存在的意义；
    把方向也管死，建议就只剩复述。
    """
    kept, _ = rules.verify_suggestions([
        {"text": "蓝屏集中在少数机型，建议先做内存与驱动的一致性排查，更换前先跑诊断",
         "basisLabels": ["蓝屏"]},
        {"text": "外设失灵较多，建议核查 USB 供电与接口氧化情况",
         "basisLabels": ["外设失灵"]},
    ], facts)
    assert len(kept) == 2


def test_建议_只剔除有问题的条目其余保留(facts):
    kept, dropped = rules.verify_suggestions([
        {"text": "对蓝屏机型做内存排查", "basisLabels": ["蓝屏"]},
        {"text": "针对不存在的故障做排查", "basisLabels": ["凭空标签"]},
    ], facts)
    assert len(kept) == 1 and len(dropped) == 1


def test_建议_空文本跳过不计入剔除(facts):
    kept, dropped = rules.verify_suggestions([{"text": "   ", "basisLabels": ["蓝屏"]}], facts)
    assert kept == [] and dropped == []


def test_已知标签集合来自facts(facts):
    labels = rules.known_labels(facts)
    assert "蓝屏" in labels and "打印机脱机" in labels
    assert "凭空标签" not in labels