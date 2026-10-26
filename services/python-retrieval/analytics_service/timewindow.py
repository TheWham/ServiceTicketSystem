# -*- coding: utf-8 -*-
"""时间窗解析（"本季度" / "近 90 天" → 具体日期区间）。

模型绝不参与日期计算 —— 这是全链路里最容易悄悄出错的一环：模型算错季度边界
不会有任何报错，只会安静地给出一个错的口径。

三个必须守住的点：

1. **季度按自然日历切，不用 `service_calendar`** —— 后者是"SLA 计时用的工作时间
   日历"（每天 9:00-18:00、跳过午休与周末），拿它算季度边界必然出错；
2. **无时间词时不默认全量** —— 落入 `DEFAULT_WINDOW_DAYS` 并在回答首句明示口径，
   绝不能把"本季度"悄悄当成"全部时间"，那会让用户以为看到的是季度数据；
3. **只输出 ISO 日期**，由 Java 侧解析；解析失败即弃用该槽位，不让非法值进 SQL。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

# 未指定时间范围时的默认窗口。给一个明确区间 + 在回答里声明口径，
# 比默认全量诚实 —— 全量会让"最近三个月"与"三年"给出同一个数字。
DEFAULT_WINDOW_DAYS = 90

SOURCE_PARSED = "规则解析"
SOURCE_DEFAULT = "默认最近90天"


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    label: str
    source: str

    @property
    def start_iso(self) -> str:
        return self.start.isoformat()

    @property
    def end_iso(self) -> str:
        return self.end.isoformat()

    def as_dict(self) -> dict:
        return {"label": self.label, "start": self.start_iso, "end": self.end_iso,
                "source": self.source}

    def days(self) -> int:
        return (self.end - self.start).days + 1


def _today(now: Optional[datetime]) -> date:
    ref = now or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return ref.astimezone(timezone.utc).date()


def quarter_of(d: date) -> int:
    return (d.month - 1) // 3 + 1


def quarter_bounds(year: int, quarter: int) -> tuple:
    """自然季度的首末日。"""
    start_month = (quarter - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    if end_month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, end_month + 1, 1) - timedelta(days=1)
    return start, end


def month_bounds(year: int, month: int) -> tuple:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def parse_window(text: str, now: Optional[datetime] = None) -> Window:
    """解析时间范围。识别不了就返回默认窗口 —— 调用方据 `source` 决定是否声明口径。

    识别不了的**不报错**：分析型提问常带各种口语时间词，为每个没见过的说法抛异常
    会让整条链路变得脆。但必须通过 `source` 让上游知道"这是默认值不是用户意图"。
    """
    raw = (text or "")
    t = raw.lower()
    today = _today(now)
    q = quarter_of(today)

    # ---- 季度 ----
    if "上一季度" in raw or "上个季度" in raw or "上季度" in raw:
        py, pq = (today.year - 1, 4) if q == 1 else (today.year, q - 1)
        s, e = quarter_bounds(py, pq)
        return Window(s, e, f"{py} Q{pq}", SOURCE_PARSED)

    m_q = re.search(r"\bq([1-4])\b", t)
    if m_q:
        qn = int(m_q.group(1))
        yr = today.year
        m_y = re.search(r"(20\d{2})", t)
        if m_y:
            yr = int(m_y.group(1))
        s, e = quarter_bounds(yr, qn)
        return Window(s, e, f"{yr} Q{qn}", SOURCE_PARSED)

    if "本季度" in raw or "这个季度" in raw or "这季度" in raw or "当季" in raw:
        s, _ = quarter_bounds(today.year, q)
        return Window(s, today, f"{today.year} Q{q}（至今）", SOURCE_PARSED)

    # ---- 月份 ----
    if "上个月" in raw or "上月" in raw:
        py, pm = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        s, e = month_bounds(py, pm)
        return Window(s, e, f"{py}-{pm:02d}", SOURCE_PARSED)

    if "本月" in raw or "这个月" in raw:
        s, _ = month_bounds(today.year, today.month)
        return Window(s, today, f"{today.year}-{today.month:02d}（至今）", SOURCE_PARSED)

    # ---- 相对天数 ----
    m_days = re.search(r"(?:近|最近|过去|前)\s*(\d+)\s*(?:天|日)", raw)
    if m_days:
        n = max(1, min(int(m_days.group(1)), 3650))
        return Window(today - timedelta(days=n - 1), today, f"近 {n} 天", SOURCE_PARSED)

    m_weeks = re.search(r"(?:近|最近|过去|前)\s*(\d+)\s*(?:周|个?星期)", raw)
    if m_weeks:
        n = max(1, min(int(m_weeks.group(1)), 520))
        return Window(today - timedelta(days=n * 7 - 1), today, f"近 {n} 周", SOURCE_PARSED)

    m_months = re.search(r"(?:近|最近|过去|前)\s*(\d+)\s*个?月", raw)
    if m_months:
        n = max(1, min(int(m_months.group(1)), 120))
        return Window(today - timedelta(days=n * 30), today, f"近 {n} 个月", SOURCE_PARSED)

    # ---- 年份 ----
    if "今年" in raw or "本年" in raw:
        return Window(date(today.year, 1, 1), today, f"{today.year} 年（至今）", SOURCE_PARSED)

    m_year = re.search(r"(20\d{2})\s*年", raw)
    if m_year:
        yr = int(m_year.group(1))
        return Window(date(yr, 1, 1), date(yr, 12, 31), f"{yr} 年", SOURCE_PARSED)

    # ---- 默认 ----
    return Window(today - timedelta(days=DEFAULT_WINDOW_DAYS - 1), today,
                  f"近 {DEFAULT_WINDOW_DAYS} 天", SOURCE_DEFAULT)


def is_explicit(text: str, now: Optional[datetime] = None) -> bool:
    """提问里是否显式给了时间范围（用于决定要不要回问澄清）。"""
    return parse_window(text, now).source == SOURCE_PARSED