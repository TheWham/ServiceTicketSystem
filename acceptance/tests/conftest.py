# -*- coding: utf-8 -*-
"""pytest 公共夹具：FixedClock(2026-09-21 12:00) + 全新 :memory: 库 + CMDB/用户种子数据。
评测环境对应《验收评测协议书》§1.3：CMDB 已灌入 TC-01/03/05/08 资产编号。"""
import pytest

from ticket_p0.clock import FixedClock
from ticket_p0.constants import Role
from ticket_p0.service import TicketService
from ticket_p0.storage import SQLiteStore

# 样本文件字节：合法 JPEG / 合法 PNG / EXE 可执行（MZ 头，TC-10 伪装向量）
JPG_BYTES = b"\xff\xd8\xff" + bytes(64)
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + bytes(64)
EXE_BYTES = b"MZ" + bytes(64)


@pytest.fixture
def clock():
    """固定评测时刻 2026-09-21 12:00:00：TC-01 期望时间 18:00 合法、TC-09 的 2020 年非法"""
    return FixedClock(2026, 9, 21, 12, 0, 0)


@pytest.fixture
def service(clock):
    svc = TicketService(SQLiteStore(":memory:"), clock)
    # 用户：员工 / 工程师 / 主管
    svc.seed_user("E1001", Role.EMPLOYEE)
    svc.seed_user("E2001", Role.ENGINEER)
    svc.seed_user("E9001", Role.SUPERVISOR)
    # CMDB 模拟数据（协议书 §六-1：评测前必须灌库，否则 M-09 误判）
    svc.seed_asset("IT-PC-20260901", "办公电脑", "ThinkCentre M920t", "E1001")
    svc.seed_asset("IT-NW-20260815", "VPN 网关", "AnyConnect Gateway", "E2001")
    svc.seed_asset("IT-PR-20240820", "公共打印机", "HP LaserJet Pro", "E1001")
    svc.seed_asset("IT-AB-12345678", "边界资产", "Boundary Model X", "E1001")
    return svc


@pytest.fixture
def make_dto():
    """DTO 工厂：默认合法（TC-01 形态精简版），测试按需覆盖字段"""
    def _make(**over):
        dto = {
            "title": "办公电脑开机蓝屏报错0x0000007B反复重启",
            "category": "HARDWARE",
            "priority": "MEDIUM",
            "description": "今早9点开机出现蓝屏错误代码0x0000007B，反复重启无法进入系统。",
            "assetId": None,
            "attachmentUrls": [],
            "expectedFinishTime": None,
        }
        dto.update(over)
        return dto
    return _make
