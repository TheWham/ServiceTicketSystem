# -*- coding: utf-8 -*-
"""工单流转日志审计脚本 —— ticket-flow-audit Skill 支撑脚本

扫描 SQLite ticket_flow_log 表，按 SPEC §3.1 十三合法边基准检测六类违规：
R1 非法流转边 / R2 终态后操作 / R3 首条日志异常 / R4 必填备注缺失 / R5 时间倒序 / R6 越权操作

用法:
    python audit_flow_log.py --db ticket.db            # 审计真实库
    python audit_flow_log.py --db ticket.db --json    # JSON 输出(CI 用)
    python audit_flow_log.py --demo                    # 内置样本自检(无库演示)

退出码: 0=干净  1=发现违规  2=参数/环境错误
只读审计,不写库。
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

# ---------------- 基准定义(与 acceptance/src/ticket_p0/state_machine.py 同源) ----------------
# SPEC §3.1 十三合法边: (from_status, action) -> (to_status, roles, remark_required)
# roles 为空集 = 不限角色; SUPERVISOR 全局放行
EDGES = {
    (None, "SUBMIT"): ("CREATED", {"EMPLOYEE"}, False),
    ("CREATED", "ACCEPT"): ("ASSIGNED", {"ENGINEER"}, False),
    ("ASSIGNED", "REQUEST_SUPPLEMENT"): ("PENDING_SUPPLEMENT", {"ENGINEER"}, True),
    ("PENDING_SUPPLEMENT", "SUPPLEMENT"): ("ASSIGNED", {"EMPLOYEE"}, False),
    ("ASSIGNED", "TRANSFER_EXTERNAL"): ("PENDING_EXTERNAL", {"ENGINEER"}, True),
    ("PENDING_EXTERNAL", "RESUME"): ("ASSIGNED", {"ENGINEER"}, False),
    ("ASSIGNED", "RESOLVE"): ("PENDING_ACCEPTANCE", {"ENGINEER"}, False),
    ("REJECTED", "REWORK"): ("ASSIGNED", {"ENGINEER"}, False),
    ("PENDING_ACCEPTANCE", "ACCEPT_APPROVE"): ("ACCEPTED", {"EMPLOYEE"}, False),
    ("PENDING_ACCEPTANCE", "ACCEPT_REJECT"): ("REJECTED", {"EMPLOYEE"}, True),
    ("ACCEPTED", "CLOSE"): ("CLOSED", {"EMPLOYEE"}, False),
    ("REJECTED", "CLOSE"): ("CLOSED", {"EMPLOYEE"}, False),
    ("CREATED", "CLOSE"): ("CLOSED", {"EMPLOYEE"}, False),
}
TERMINAL_STATES = {"ACCEPTED", "CLOSED"}
SUPERVISOR_BYPASS = "SUPERVISOR"


def load_flow_logs(db_path):
    """从 SQLite 读取流转日志,按 (ticket_id, created_at, log_id) 排序。"""
    conn = sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT log_id, ticket_id, from_status, to_status, action, "
            "operator_id, operator_role, remark, created_at "
            "FROM ticket_flow_log ORDER BY ticket_id, created_at, log_id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def audit_ticket(logs):
    """审计单个工单的日志序列,返回违规列表。"""
    violations = []

    # R3: 首条日志必须是 (起点)→CREATED
    first = logs[0]
    if not (first["from_status"] is None and first["to_status"] == "CREATED"):
        violations.append({
            "rule": "R3", "severity": "HIGH", "log_id": first["log_id"],
            "ticket_id": first["ticket_id"],
            "detail": f"首条流转不是 (起点)→CREATED, 实际: {first['from_status']}→{first['to_status']}",
        })

    for i, log in enumerate(logs):
        key = (log["from_status"], log["action"])
        edge = EDGES.get(key)

        # R1: 非法流转边
        if edge is None:
            violations.append({
                "rule": "R1", "severity": "CRITICAL", "log_id": log["log_id"],
                "ticket_id": log["ticket_id"],
                "detail": f"非法流转边: {log['from_status']} --{log['action']}--> {log['to_status']}",
            })
            continue
        to_expected, roles, remark_required = edge

        # 目标状态不一致(边存在但 to 不符)
        if log["to_status"] != to_expected:
            violations.append({
                "rule": "R1", "severity": "CRITICAL", "log_id": log["log_id"],
                "ticket_id": log["ticket_id"],
                "detail": f"流转边目标态不符: {log['from_status']} --{log['action']}--> "
                          f"{log['to_status']}, SPEC 要求 → {to_expected}",
            })

        # R6: 越权操作
        role = log.get("operator_role")
        if roles and role not in roles and role != SUPERVISOR_BYPASS:
            violations.append({
                "rule": "R6", "severity": "CRITICAL", "log_id": log["log_id"],
                "ticket_id": log["ticket_id"],
                "detail": f"越权操作: 角色 {role} 执行了 {log['from_status']} --{log['action']}--> "
                          f"{log['to_status']}, 允许角色: {sorted(roles)}",
            })

        # R4: 必填备注缺失
        if remark_required and not (log.get("remark") or "").strip():
            violations.append({
                "rule": "R4", "severity": "HIGH", "log_id": log["log_id"],
                "ticket_id": log["ticket_id"],
                "detail": f"必填备注缺失: {log['from_status']} --{log['action']}--> {log['to_status']} "
                          f"要求 remark 非空",
            })

        # R2: 终态后操作(检查当前日志之后是否还有记录)
        if i + 1 < len(logs) and log["to_status"] in TERMINAL_STATES:
            nxt = logs[i + 1]
            violations.append({
                "rule": "R2", "severity": "CRITICAL", "log_id": nxt["log_id"],
                "ticket_id": nxt["ticket_id"],
                "detail": f"终态后操作: 工单已进入 {log['to_status']}, 仍存在后续流转 "
                          f"{nxt['from_status']} --{nxt['action']}--> {nxt['to_status']}",
            })

        # R5: 时间倒序
        if i + 1 < len(logs):
            nxt = logs[i + 1]
            if nxt["created_at"] < log["created_at"]:
                violations.append({
                    "rule": "R5", "severity": "MEDIUM", "log_id": nxt["log_id"],
                    "ticket_id": nxt["ticket_id"],
                    "detail": f"时间倒序: log {log['log_id']}({log['created_at']}) 之后 "
                              f"log {nxt['log_id']}({nxt['created_at']}) 更早",
                })

    return violations


def group_by_ticket(logs):
    """按 ticket_id 分组,保持组内时间序。"""
    grouped = {}
    for log in logs:
        grouped.setdefault(log["ticket_id"], []).append(log)
    return grouped


def run_audit(logs):
    """执行全量审计,返回 (violations, stats)。"""
    grouped = group_by_ticket(logs)
    all_violations = []
    for ticket_id in sorted(grouped):
        all_violations.extend(audit_ticket(grouped[ticket_id]))
    stats = {
        "total_tickets": len(grouped),
        "total_logs": len(logs),
        "violations": len(all_violations),
        "by_severity": {},
        "by_rule": {},
    }
    for v in all_violations:
        stats["by_severity"][v["severity"]] = stats["by_severity"].get(v["severity"], 0) + 1
        stats["by_rule"][v["rule"]] = stats["by_rule"].get(v["rule"], 0) + 1
    return all_violations, stats


# ---------------- 内置演示样本(含 7 类违规各至少 1 条) ----------------
def demo_logs():
    """构造带违规的演示数据: 正常链路 + 6 类违规样本(R1~R6 各至少 1 条)。"""
    return [
        # 工单 T-001: 完全正常链路 CREATED→ASSIGNED→PENDING_ACCEPTANCE→ACCEPTED
        {"log_id": 1, "ticket_id": "T-001", "from_status": None, "to_status": "CREATED",
         "action": "SUBMIT", "operator_id": "u-emp-01", "operator_role": "EMPLOYEE",
         "remark": "", "created_at": "2026-09-20 09:00:00"},
        {"log_id": 2, "ticket_id": "T-001", "from_status": "CREATED", "to_status": "ASSIGNED",
         "action": "ACCEPT", "operator_id": "u-eng-01", "operator_role": "ENGINEER",
         "remark": "", "created_at": "2026-09-20 09:10:00"},
        {"log_id": 3, "ticket_id": "T-001", "from_status": "ASSIGNED", "to_status": "PENDING_ACCEPTANCE",
         "action": "RESOLVE", "operator_id": "u-eng-01", "operator_role": "ENGINEER",
         "remark": "已更换内存条", "created_at": "2026-09-20 11:00:00"},
        {"log_id": 4, "ticket_id": "T-001", "from_status": "PENDING_ACCEPTANCE", "to_status": "ACCEPTED",
         "action": "ACCEPT_APPROVE", "operator_id": "u-emp-01", "operator_role": "EMPLOYEE",
         "remark": "", "created_at": "2026-09-20 14:00:00"},

        # 工单 T-002: R1 非法边(CREATED 直接跳 PENDING_ACCEPTANCE)
        {"log_id": 5, "ticket_id": "T-002", "from_status": None, "to_status": "CREATED",
         "action": "SUBMIT", "operator_id": "u-emp-02", "operator_role": "EMPLOYEE",
         "remark": "", "created_at": "2026-09-21 10:00:00"},
        {"log_id": 6, "ticket_id": "T-002", "from_status": "CREATED", "to_status": "PENDING_ACCEPTANCE",
         "action": "RESOLVE", "operator_id": "u-emp-02", "operator_role": "EMPLOYEE",
         "remark": "", "created_at": "2026-09-21 10:05:00"},

        # 工单 T-005: R6 越权(边合法但角色不符: EMPLOYEE 执行了仅 ENGINEER 可做的 REQUEST_SUPPLEMENT)
        {"log_id": 12, "ticket_id": "T-005", "from_status": None, "to_status": "CREATED",
         "action": "SUBMIT", "operator_id": "u-emp-05", "operator_role": "EMPLOYEE",
         "remark": "", "created_at": "2026-09-22 10:00:00"},
        {"log_id": 13, "ticket_id": "T-005", "from_status": "CREATED", "to_status": "ASSIGNED",
         "action": "ACCEPT", "operator_id": "u-eng-04", "operator_role": "ENGINEER",
         "remark": "", "created_at": "2026-09-22 10:10:00"},
        {"log_id": 14, "ticket_id": "T-005", "from_status": "ASSIGNED", "to_status": "PENDING_SUPPLEMENT",
         "action": "REQUEST_SUPPLEMENT", "operator_id": "u-emp-05", "operator_role": "EMPLOYEE",
         "remark": "请补充", "created_at": "2026-09-22 10:20:00"},  # 角色应为 ENGINEER → R6

        # 工单 T-003: R2 终态后操作(ACCEPTED 后又有一条) + R5 时间倒序
        {"log_id": 7, "ticket_id": "T-003", "from_status": None, "to_status": "CREATED",
         "action": "SUBMIT", "operator_id": "u-emp-03", "operator_role": "EMPLOYEE",
         "remark": "", "created_at": "2026-09-21 11:00:00"},
        {"log_id": 8, "ticket_id": "T-003", "from_status": "CREATED", "to_status": "ACCEPTED",
         "action": "ACCEPT", "operator_id": "u-eng-02", "operator_role": "ENGINEER",
         "remark": "", "created_at": "2026-09-21 11:30:00"},
        {"log_id": 9, "ticket_id": "T-003", "from_status": "ACCEPTED", "to_status": "ASSIGNED",
         "action": "REWORK", "operator_id": "u-eng-02", "operator_role": "ENGINEER",
         "remark": "", "created_at": "2026-09-21 11:20:00"},  # 时间早于上一条 → R5

        # 工单 T-004: R4 必填备注缺失(REQUEST_SUPPLEMENT 无 remark), 链路完整
        {"log_id": 10, "ticket_id": "T-004", "from_status": None, "to_status": "CREATED",
         "action": "SUBMIT", "operator_id": "u-emp-04", "operator_role": "EMPLOYEE",
         "remark": "", "created_at": "2026-09-22 08:00:00"},
        {"log_id": 11, "ticket_id": "T-004", "from_status": "CREATED", "to_status": "ASSIGNED",
         "action": "ACCEPT", "operator_id": "u-eng-03", "operator_role": "ENGINEER",
         "remark": "", "created_at": "2026-09-22 08:30:00"},
        {"log_id": 15, "ticket_id": "T-004", "from_status": "ASSIGNED", "to_status": "PENDING_SUPPLEMENT",
         "action": "REQUEST_SUPPLEMENT", "operator_id": "u-eng-03", "operator_role": "ENGINEER",
         "remark": "", "created_at": "2026-09-22 09:00:00"},  # remark 为空 → R4
    ]


def main():
    parser = argparse.ArgumentParser(description="工单流转日志审计(SPEC §3.1 基准)")
    parser.add_argument("--db", help="SQLite 数据库路径(只读审计)")
    parser.add_argument("--demo", action="store_true", help="使用内置违规样本自检")
    parser.add_argument("--json", action="store_true", help="JSON 输出(CI 集成)")
    args = parser.parse_args()

    if args.demo:
        logs = demo_logs()
        source = "demo"
    elif args.db:
        if not Path(args.db).exists():
            print(f"ERROR: 数据库不存在: {args.db}", file=sys.stderr)
            sys.exit(2)
        logs = load_flow_logs(args.db)
        source = str(Path(args.db).resolve())
    else:
        parser.print_help()
        sys.exit(2)

    violations, stats = run_audit(logs)

    if args.json:
        print(json.dumps({"source": source, "stats": stats, "violations": violations},
                         ensure_ascii=False, indent=2))
    else:
        print(f"=== 工单流转日志审计报告 ===")
        print(f"数据源: {source}")
        print(f"工单数: {stats['total_tickets']}  日志数: {stats['total_logs']}")
        print(f"违规数: {stats['violations']}")
        if stats["by_severity"]:
            print(f"按严重度: {json.dumps(stats['by_severity'], ensure_ascii=False)}")
        if stats["by_rule"]:
            print(f"按规则:   {json.dumps(stats['by_rule'], ensure_ascii=False)}")
        print()
        for v in violations:
            print(f"[{v['severity']}] {v['rule']} | {v['ticket_id']} | log#{v['log_id']} | {v['detail']}")
        print()
        if violations:
            print("判定: 未通过 —— 存在违规, 禁止发布")
        else:
            print("判定: 通过 —— 未发现违规")

    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
