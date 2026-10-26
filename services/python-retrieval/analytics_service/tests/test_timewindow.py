# -*- coding: utf-8 -*-
"""时间窗解析的单测。

日期算错不会报错，只会安静地给一个错的口径 —— 所以边界必须逐条钉死。
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from analytics_service import timewindow as tw

NOW = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)


def parse(text):
    return tw.parse_window(text, NOW)


# ---------------------------------------------------------------- 季度

def test_本季度到今日():
    w = parse("总结本季度的共性根因")
    assert w.start == date(2026, 10, 1)
    assert w.end == date(2026, 10, 26)
    assert w.label == "2026 Q4（至今）"
    assert w.source == tw.SOURCE_PARSED


def test_上一季度():
    w = parse("对比上一季度的趋势")
    assert (w.start, w.end) == (date(2026, 7, 1), date(2026, 9, 30))
    assert w.label == "2026 Q3"


def test_Q2带年份():
    w = parse("看看 Q2 的分布")
    assert (w.start, w.end) == (date(2026, 4, 1), date(2026, 6, 30))


def test_Q1跨年回退():
    """1 月的"上一季度"必须回到去年 Q4，不能算成今年 Q0。"""
    w = tw.parse_window("上一季度", datetime(2026, 1, 15, tzinfo=timezone.utc))
    assert (w.start, w.end) == (date(2025, 10, 1), date(2025, 12, 31))


@pytest.mark.parametrize("q,start,end", [
    (1, date(2026, 1, 1), date(2026, 3, 31)),
    (2, date(2026, 4, 1), date(2026, 6, 30)),
    (3, date(2026, 7, 1), date(2026, 9, 30)),
    (4, date(2026, 10, 1), date(2026, 12, 31)),
])
def test_季度边界(q, start, end):
    assert tw.quarter_bounds(2026, q) == (start, end)


# ---------------------------------------------------------------- 相对窗口

def test_近九十天含今天():
    w = parse("最近 90 天的情况")
    assert w.end == date(2026, 10, 26)
    assert w.days() == 90


def test_上个月():
    w = parse("上个月的工单")
    assert (w.start, w.end) == (date(2026, 9, 1), date(2026, 9, 30))


def test_今年():
    w = parse("今年的故障趋势")
    assert (w.start, w.end) == (date(2026, 1, 1), date(2026, 10, 26))


# ---------------------------------------------------------------- 默认口径

def test_无时间词走默认窗口且标明来源():
    """不能悄悄把"没说时间"当成"全部时间" —— 那会让用户以为看的是季度数据。"""
    w = parse("统计一下各类故障")
    assert w.source == tw.SOURCE_DEFAULT
    assert w.days() == tw.DEFAULT_WINDOW_DAYS
    assert "默认" in w.label or "近" in w.label


def test_is_explicit区分显式与默认():
    assert tw.is_explicit("本季度怎么样", NOW) is True
    assert tw.is_explicit("统计各类故障", NOW) is False


def test_无法识别的时间词不抛异常而是走默认():
    """分析型提问里时间说法五花八门，为没见过的说法抛异常会让链路变得很脆。"""
    w = parse("自打我入职以来")
    assert w.source == tw.SOURCE_DEFAULT


def test_窗口as_dict含来源():
    d = parse("本季度").as_dict()
    assert set(d) == {"label", "start", "end", "source"}
    assert d["start"] == "2026-10-01"