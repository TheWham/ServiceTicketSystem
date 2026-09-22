# -*- coding: utf-8 -*-
"""时钟抽象：生产用 SystemClock，测试用 FixedClock（保证 3s 幂等窗、2h 超时扫描确定性）"""
from datetime import datetime, timedelta


class SystemClock:
    def now(self) -> datetime:
        return datetime.now()


class FixedClock:
    """测试时钟：固定时刻，可 advance 推进"""

    def __init__(self, year=2026, month=9, day=21, hour=12, minute=0, second=0):
        self._now = datetime(year, month, day, hour, minute, second)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float):
        self._now = self._now + timedelta(seconds=seconds)
