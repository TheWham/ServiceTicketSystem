# -*- coding: utf-8 -*-
"""共享夹具：迷你语料 + 词表。

刻意**不联网、不读远程库** —— 单测要能在任何环境秒跑；真实数据的端到端验证
由 `analytics_service.pipelines.demo_analytics` 与 unmatched_report 承担。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analytics_service import taxonomy as tx
from analytics_service.contract import TicketRow
from analytics_service.data_source import FixtureDataSource

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "tickets_mini.json"


@pytest.fixture(scope="session")
def taxonomy():
    """真实词表（configs/taxonomy.yaml）。词表本身不合规时这里就会抛错。"""
    return tx.load_taxonomy(use_cache=False)


@pytest.fixture
def rows() -> list:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return [TicketRow.from_dict(i) for i in raw["tickets"]]


@pytest.fixture
def ds(rows) -> FixtureDataSource:
    return FixtureDataSource(rows)


@pytest.fixture
def by_id(rows) -> dict:
    return {r.ticket_id: r for r in rows}


@pytest.fixture
def ds_failing(rows) -> FixtureDataSource:
    """取数失败：链路应如实拒答，**不得用模型通用知识替代**。"""
    return FixtureDataSource(rows, fail="模拟工单系统不可用")


class _BoomDataSource:
    """抛非 ScanError 的异常：验证节点异常会被记录且链路不中断。"""

    def scan_tickets(self, window, category=""):
        raise RuntimeError("模拟未预期的运行时异常")


@pytest.fixture
def ds_boom() -> _BoomDataSource:
    return _BoomDataSource()