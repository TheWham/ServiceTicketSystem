# -*- coding: utf-8 -*-
"""数据源单测：重点守住「知识只返回已发布当前版本」这条验收红线。"""

import pytest

from workflow_demo.data_source import SqliteDataSource
from workflow_demo.contract import TicketDraft


@pytest.fixture()
def ds(tmp_path):
    return SqliteDataSource(db_path=str(tmp_path / "demo.db"))


# ---------------------------------------------------------------- 知识检索

def test_search_只返回当前版本(ds):
    """KA-VPN-CONNECT 有 v1 旧版与 v2 现行版，只能召回 v2。"""
    items = ds.search_knowledge("VPN 连不上 拨号 超时")
    assert items, "应命中 VPN 条目"
    top = items[0]
    assert top.article_id == "KA-VPN-CONNECT"
    assert top.version_id == "KV-VPN-CONNECT-2"
    assert top.version_no == 2
    assert all(i.version_id != "KV-VPN-CONNECT-1" for i in items)


def test_search_不返回已下线文章(ds):
    """KA-OLD-MAIL 是 OFFLINE，任何查询都不得召回（AC-27 / RD-006）。"""
    items = ds.search_knowledge("邮箱迁移怎么弄")
    assert all(i.article_id != "KA-OLD-MAIL" for i in items)
    assert items == []


def test_search_无命中返回空(ds):
    assert ds.search_knowledge("我想申请年假流程") == []


def test_search_按分类过滤(ds):
    items = ds.search_knowledge("打印机离线", category_id="C_NET")
    assert items == []


# ---------------------------------------------------------------- 工单

def test_list_my_tickets_只看本人(ds):
    mine = ds.list_my_tickets("U_EMP01")
    assert {t.ticket_id for t in mine} == {"T20260115-001", "T20260115-002", "T20251220-007"}
    assert ds.list_my_tickets("U_ENG01") == []


def test_find_open_tickets_窗口内且未结束(ds):
    """2 小时前提交、状态 IN_PROGRESS 的打印机工单 → 命中。"""
    hits = ds.find_open_tickets("U_EMP01", "C_HW_PR", within_hours=24)
    assert [t.ticket_id for t in hits] == ["T20260115-001"]


def test_find_open_tickets_终态不算重复(ds):
    """C_HW_PC 那张单是 CLOSED，即使窗口放宽也不能算重复。"""
    assert ds.find_open_tickets("U_EMP01", "C_HW_PC", within_hours=24 * 365) == []


def test_find_open_tickets_窗口外不算重复(ds):
    """1 天前那张 C_NET 工单，用 1 小时窗口应落空。"""
    assert ds.find_open_tickets("U_EMP01", "C_NET", within_hours=1) == []


# ---------------------------------------------------------------- 决策表

@pytest.mark.parametrize("category_id,team_id,team_name", [
    ("C_HW_PC", "T_HW", "硬件支持组"),
    ("C_HW_PR", "T_HW", "硬件支持组"),
    ("C_NET", "T_NET", "网络支持组"),
    ("C_ACC", "T_SW", "软件支持组"),
])
def test_resolve_team_走决策表(ds, category_id, team_id, team_name):
    assert ds.resolve_team(category_id) == (team_id, team_name)


def test_resolve_team_未知分类返回空(ds):
    assert ds.resolve_team("C_NOT_EXIST") is None


def test_sla_targets_照抄_PRD(ds):
    """PRD 11.3：高 4 工作小时 / 中 1 工作日 / 低 3 工作日；11.2：响应 10 工作分钟。"""
    targets = ds.sla_targets()
    assert targets["HIGH"] == {"responseTargetSeconds": 600, "completionTargetSeconds": 14400}
    assert targets["MEDIUM"]["completionTargetSeconds"] == 28800
    assert targets["LOW"]["completionTargetSeconds"] == 86400


def test_service_calendar(ds):
    cal = ds.service_calendar()
    assert cal["workStart"] == "09:00" and cal["workEnd"] == "18:00"
    assert cal["workdaySeconds"] == 28800


# ---------------------------------------------------------------- 建单草稿

def test_create_draft_不落库(ds, tmp_path):
    draft = ds.create_draft("U_EMP01", TicketDraft(title="标题", description="描述",
                                                  category_id="C_HW_PC", priority="HIGH"))
    assert draft["status"] == "PENDING_EMPLOYEE_CONFIRM"
    assert draft["draftId"].startswith("DRAFT-")

    # 草稿只在内存里，重建数据源后不复存在 —— 证明没写库
    fresh = SqliteDataSource(db_path=ds.db_path)
    assert fresh.drafts() == []


def test_rebuild_可重置种子(ds):
    ds.rebuild()
    assert len(ds.list_my_tickets("U_EMP01")) == 3