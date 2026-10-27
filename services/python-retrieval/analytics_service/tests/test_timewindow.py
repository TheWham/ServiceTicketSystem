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

# ================================================================ 模型槽位（Node A）

NOW_Q3 = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)


def resolve(question, slot, now=NOW_Q3):
    return tw.resolve_window(question, slot, now)


# ---------------------------------------------------------------- 槽位 → 日期

def test_年月不被年份分支截胡():
    """"2026年10月"里含"2026年"，年份分支排在前面会把它整年吞掉 —— 那是错答案。"""
    w = tw.parse_window("2026年10月的故障", NOW_Q3)
    assert (w.start, w.end) == (date(2026, 10, 1), date(2026, 10, 31))
    assert w.label == "2026-10"
    assert w.source == tw.SOURCE_PARSED


def test_月份越界不在此处报错而是退回整年():
    """'2026年13月'这种输入不该抛异常把链路打断，按'2026 年'处理即可。"""
    w = tw.parse_window("2026年13月", NOW_Q3)
    assert w.label == "2026 年"


@pytest.mark.parametrize("question,slot,label,days", [
    ("总结本季度的共性根因",
     {"kind": "QUARTER", "anchor": "CURRENT", "rawText": "本季度"}, "2026 Q4（至今）", None),
    ("上个月的工单",
     {"kind": "MONTH", "anchor": "PREVIOUS", "rawText": "上个月"}, "2026-09", None),
    ("最近 90 天的情况",
     {"kind": "RELATIVE", "amount": 90, "unit": "DAY", "rawText": "最近 90 天"}, "近 90 天", 90),
    ("今年的故障趋势",
     {"kind": "YEAR", "anchor": "CURRENT", "rawText": "今年"}, "2026 年（至今）", None),
    ("近 2 周的情况",
     {"kind": "RELATIVE", "amount": 2, "unit": "WEEK", "rawText": "近 2 周"}, "近 2 周", 14),
])
def test_槽位与正则口径逐日一致(question, slot, label, days):
    """两条路径算出来的必须是同一个区间 —— 否则"同一个提问走哪条路"会改变结论。"""
    model = tw.window_from_slots(slot, question, NOW_Q3)[0]
    rule = tw.parse_window(question, NOW_Q3)
    assert model is not None and model.label == label
    assert (model.start, model.end) == (rule.start, rule.end)
    if days is not None:
        assert model.days() == days
    assert resolve(question, slot).conflict is False


def test_中文数字的时间说法只有模型接得住():
    """正则的相对窗口分支要求阿拉伯数字："近两周"它一条都不命中，直接落默认 90 天。

    这正是把时间理解交给模型的意义 —— 它补的不是"更准"，是"原来根本接不住"。
    """
    rule = tw.parse_window("近两周的故障", NOW_Q3)
    assert rule.source == tw.SOURCE_DEFAULT, "正则确实没接住"

    slot, why = tw.window_from_slots(
        {"kind": "RELATIVE", "amount": 2, "unit": "WEEK", "rawText": "近两周"},
        "近两周的故障", NOW_Q3)
    assert slot is not None and slot.label == "近 2 周", why
    assert slot.days() == 14


def test_since是起点到今天而不是整月():
    """"自9月以来"若算成 9/1~9/30，10 月的数据会被整个漏掉，而结果看着完全正常。"""
    w = tw.window_from_slots({"kind": "SINCE", "month": 9, "rawText": "自9月以来"},
                             "统计自9月以来的故障", NOW_Q3)[0]
    assert (w.start, w.end) == (date(2026, 9, 1), date(2026, 10, 26))
    assert w.source == tw.SOURCE_MODEL


def test_absolute缺年份时取最近一个已经开始的周期():
    """一月里问"第三季度"，人指的是**去年** Q3。

    用 today.year 会答成十个月之后 —— 那个区间里一张工单都没有，统计结果为空，
    却看不出哪里错了。
    """
    jan = datetime(2026, 1, 15, tzinfo=timezone.utc)
    w = tw.window_from_slots({"kind": "QUARTER", "anchor": "ABSOLUTE", "quarter": 3,
                              "rawText": "第三季度"}, "第三季度的根因", jan)[0]
    assert (w.start, w.end) == (date(2025, 7, 1), date(2025, 9, 30))

    # 已经开始的季度则取今年
    w2 = tw.window_from_slots({"kind": "QUARTER", "anchor": "ABSOLUTE", "quarter": 3,
                               "rawText": "第三季度"}, "第三季度的根因", NOW_Q3)[0]
    assert w2.label == "2026 Q3"


def test_去年同期():
    w = tw.window_from_slots({"kind": "QUARTER", "anchor": "LAST_YEAR_SAME",
                              "rawText": "去年同期"}, "去年同期的情况", NOW_Q3)[0]
    assert (w.start, w.end) == (date(2025, 10, 1), date(2025, 12, 31))


# ---------------------------------------------------------------- 显式区间校验

_RAW = "7月1日到9月30日"


@pytest.mark.parametrize("start,end,expected", [
    ("2026-07-01", "2026-09-30", (date(2026, 7, 1), date(2026, 9, 30))),
    ("2026-01-01", "2026-09-30", (date(2026, 1, 1), date(2026, 9, 30))),
    ("2026-09-30", "2026-07-01", None),      # 次序颠倒
    ("2026-7-1", "2026-09-30", None),        # 格式非法（非零填充）
    ("2001-01-01", "2026-09-30", None),      # 早于量程下限
    ("2026-01-01", "2030-01-01", None),      # 跨度超过 3650 天
    ("2026-01-01", None, None),              # 缺一端
])
def test_显式区间只做校验不做推算(start, end, expected):
    """日期区间错了不会报错，只会安静地改变分母 —— 三道校验一道都不能省。"""
    q = "统计从7月1日到9月30日的工单"
    w, why = tw.window_from_slots(
        {"kind": "EXPLICIT_RANGE", "startDate": start, "endDate": end, "rawText": _RAW},
        q, NOW_Q3)
    assert (w is not None) is (expected is not None), why
    if expected:
        assert (w.start, w.end) == expected


# ---------------------------------------------------------------- 反幻觉闸门

@pytest.mark.parametrize("raw", ["", "   ", "上个月", "最近30天"])
def test_rawText必须在提问里字面出现(raw):
    """与数字门禁同构：模型编一个用户根本没说过的时间，当场作废。"""
    slot = {"kind": "MONTH", "anchor": "PREVIOUS", "rawText": raw}
    w, why = tw.window_from_slots(slot, "第三季度的共性根因", NOW_Q3)
    assert w is None and why


def test_模型说没有时间词而正则字面命中时采信规则():
    """提问里明明写着"本季度"，模型却说没有 —— 字面命中是硬证据。"""
    r = resolve("本季度的分布", {"kind": "NONE"})
    assert r.window.source == tw.SOURCE_PARSED
    assert r.model_missed is True


# ---------------------------------------------------------------- 仲裁

def test_正则退回默认窗口时模型接管不算冲突():
    """**这条是防 Trap 1 回归的**。

    parse_window 在正则未命中时返回的是 SOURCE_DEFAULT（默认 90 天）而不是 None。
    不加区分地拿它和模型窗口比区间，每一条**靠模型立功救回来**的提问都会误报冲突 ——
    恰好把最该看见的那批信号淹没。
    """
    r = resolve("第三季度网络与打印设备的共性根因是什么",
                {"kind": "QUARTER", "anchor": "ABSOLUTE", "quarter": 3,
                 "rawText": "第三季度"})
    assert r.window.label == "2026 Q3" and r.from_model
    assert r.conflict is False, "正则只是退回了默认窗口，这不是冲突"
    assert r.rejected == "" and r.model_missed is False


def test_两边都字面命中且区间不同才报冲突():
    """模型把"本季度"抽成了上月 —— 两边都有字面依据，采用模型但必须留痕。"""
    r = resolve("本季度的共性根因", {"kind": "MONTH", "anchor": "PREVIOUS",
                                     "rawText": "本季度"})
    assert r.window.label == "2026-09"
    assert r.conflict is True
    assert "规则解析为" in r.note


def test_没跑模型时不记任何槽位痕迹():
    """ANALYTICS_MODEL_ROUTING=0 或模型未配置是**配置选择**，不是异常。"""
    r = resolve("本季度的共性根因", None)
    assert r.window.source == tw.SOURCE_PARSED
    assert r.rejected == "" and r.conflict is False and r.model_missed is False


def test_未知时间类型被拒():
    w, why = tw.window_from_slots({"kind": "SEASON", "rawText": "本季度"},
                                  "本季度的分布", NOW_Q3)
    assert w is None and "未知的时间类型" in why
