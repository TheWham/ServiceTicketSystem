# -*- coding: utf-8 -*-
"""工单状态机（SPEC §3.1 状态转换主表）：合法边 + Guard 守卫（角色/本人/remark/乐观锁）。
状态机中不存在的边一律 40900「非法状态流转:X -> Y」。"""
from dataclasses import dataclass, field

from .constants import Role, TicketStatus as S


@dataclass(frozen=True)
class Edge:
    action: str
    to_status: str
    roles: frozenset = frozenset()     # 允许角色（空=不限）；SUPERVISOR 全局放行
    creator_only: bool = False         # 仅提单本人（SUPERVISOR 不放行）
    remark_required: bool = False      # remark 强制非空
    event: str = None                  # 流转钩子事件（P0 仅落库 LOG）
    receivers: str = None              # CREATOR / ASSIGNEE / CREATOR_ASSIGNEE / SUPERVISOR
    set_assignee: bool = False         # 流转后 assignee_id = 操作人
    reject_incr: bool = False          # reject_count +1


_E = Role.EMPLOYEE
_G = Role.ENGINEER

# SPEC §3.1 主表 13 条合法边（SUBMIT 边由 service.submit 落地，此处仅作元数据声明）
EDGES = {
    (None, "SUBMIT"): Edge(
        "SUBMIT", S.CREATED, roles=frozenset({_E}),
        event="SUBMIT_SUCCESS", receivers="CREATOR"),
    (S.CREATED, "ACCEPT"): Edge(
        "ACCEPT", S.ASSIGNED, roles=frozenset({_G}),
        event="DISPATCH", receivers="ASSIGNEE", set_assignee=True),
    (S.ASSIGNED, "REQUEST_SUPPLEMENT"): Edge(
        "REQUEST_SUPPLEMENT", S.PENDING_SUPPLEMENT, roles=frozenset({_G}),
        remark_required=True, event="PENDING_SUPPLEMENT", receivers="CREATOR"),
    (S.PENDING_SUPPLEMENT, "SUPPLEMENT"): Edge(
        "SUPPLEMENT", S.ASSIGNED, creator_only=True),
    (S.ASSIGNED, "TRANSFER_EXTERNAL"): Edge(
        "TRANSFER_EXTERNAL", S.PENDING_EXTERNAL, roles=frozenset({_G}),
        remark_required=True, event="PENDING_EXTERNAL", receivers="CREATOR_ASSIGNEE"),
    (S.PENDING_EXTERNAL, "RESUME"): Edge(
        "RESUME", S.ASSIGNED, roles=frozenset({_G})),
    (S.ASSIGNED, "RESOLVE"): Edge(
        "RESOLVE", S.PENDING_ACCEPTANCE, roles=frozenset({_G}),
        event="PENDING_ACCEPTANCE", receivers="CREATOR"),
    (S.REJECTED, "REWORK"): Edge(
        "REWORK", S.ASSIGNED, roles=frozenset({_G}),
        event="DISPATCH", receivers="ASSIGNEE", set_assignee=True),
    (S.PENDING_ACCEPTANCE, "ACCEPT_APPROVE"): Edge(
        "ACCEPT_APPROVE", S.ACCEPTED, creator_only=True,
        event="ACCEPT_APPROVED", receivers="ASSIGNEE"),
    (S.PENDING_ACCEPTANCE, "ACCEPT_REJECT"): Edge(
        "ACCEPT_REJECT", S.REJECTED, creator_only=True, remark_required=True,
        event="ACCEPT_REJECTED", receivers="ASSIGNEE", reject_incr=True),
    (S.ACCEPTED, "CLOSE"): Edge("CLOSE", S.CLOSED, creator_only=True),
    (S.REJECTED, "CLOSE"): Edge("CLOSE", S.CLOSED, creator_only=True),
    (S.CREATED, "CLOSE"): Edge("CLOSE", S.CLOSED, creator_only=True),
}

# 非法流转报错文案用：动作 → 预期目标状态
ACTION_TARGET = {e.action: e.to_status for e in EDGES.values()}


def resolve_edge(from_status, action) -> Edge:
    """查合法边；不存在返回 None（由调用方抛 40900）"""
    return EDGES.get((from_status, action))
