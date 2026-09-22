# -*- coding: utf-8 -*-
"""SPEC §1.8 枚举值域 / §1.7 校验阈值 / §2.1 超时阈值 / §2.7 错误码（与规格书强一致）"""
import re

# ---- 错误码（SPEC §2.7）----
CODE_OK = 0
CODE_BIZ_ERROR = 40000
CODE_UNAUTHORIZED = 40100
CODE_FORBIDDEN = 40300
CODE_NOT_FOUND = 40400
CODE_ASSET_NOT_FOUND = 40401
CODE_CONFLICT = 40900
CODE_SYSTEM_ERROR = 500


# ---- 枚举值域（SPEC §1.8，DB 存 name() 字符串）----
class TicketStatus:
    CREATED = "CREATED"                        # 待接单
    ASSIGNED = "ASSIGNED"                      # 处理中
    PENDING_SUPPLEMENT = "PENDING_SUPPLEMENT"  # 待补充
    PENDING_EXTERNAL = "PENDING_EXTERNAL"      # 待外部
    PENDING_ACCEPTANCE = "PENDING_ACCEPTANCE"  # 待验收
    ACCEPTED = "ACCEPTED"                      # 已完成（终态，仅可 CLOSED）
    REJECTED = "REJECTED"                      # 已驳回
    CLOSED = "CLOSED"                          # 已关闭（终态）

    ALL = (CREATED, ASSIGNED, PENDING_SUPPLEMENT, PENDING_EXTERNAL,
           PENDING_ACCEPTANCE, ACCEPTED, REJECTED, CLOSED)
    TERMINAL = (ACCEPTED, CLOSED)


class Role:
    EMPLOYEE = "EMPLOYEE"
    ENGINEER = "ENGINEER"
    SUPERVISOR = "SUPERVISOR"  # 对角色守卫放行（不放行 creator_only）


CATEGORIES = ("HARDWARE", "SOFTWARE", "NETWORK", "ACCOUNT", "OTHER")
PRIORITIES = ("HIGH", "MEDIUM", "LOW")
DEFAULT_PRIORITY = "MEDIUM"

# ---- 字段校验阈值（SPEC §1.7）----
TITLE_MAX_LEN = 50
DESC_MIN_LEN = 10
DESC_MAX_LEN = 500
ATTACH_MAX_COUNT = 3
ATTACH_MAX_BYTES = 5 * 1024 * 1024  # 单张 ≤5MB
ATTACH_EXTS = ("jpg", "jpeg", "png")
ASSET_ID_RE = re.compile(r"^IT-[A-Z]{2,4}-\d{8}$")
TICKET_ID_RE = re.compile(r"^TK\d{8}\d{4}$")
ATTACH_URL_RE = re.compile(r"^/files/[0-9a-f]{32}\.(jpg|jpeg|png)$")

# ---- 超时与幂等阈值（SPEC §2.1）----
SUBMIT_DEDUP_TTL_SECONDS = 3       # T1 提单防重窗口
NOTIFY_DEDUP_TTL_SECONDS = 60      # 通知事件幂等窗口
TIMEOUT_ALERT_HOURS = 2            # T2 处理中超时阈值
EXTERNAL_REMIND_HOURS = 24         # T3 待外部滞留阈值
SUPERVISOR_ID = "E9001"            # TIMEOUT_ALERT 接收人（主管）

TIME_FMT = "%Y-%m-%d %H:%M:%S"
