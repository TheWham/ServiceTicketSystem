# -*- coding: utf-8 -*-
"""状态机漂移比对脚本 —— ticket-flow-audit Skill 支撑脚本

基准 = PRD v11 §2.2 流转表(8 态英文); 对比对象 = it-ticket-cloud Java Transition.java(7 态中文)。
检测四类漂移: 边缺失 / 边多余 / 目标态不一致 / 角色守卫差异 / 状态枚举差异。

用法:
    python diff_state_machines.py                     # 默认找仓库内 Transition.java
    python diff_state_machines.py --java <path>       # 指定 Java 文件
    python diff_state_machines.py --json              # JSON 输出

退出码: 0=一致  1=有漂移  2=环境错误
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------------- 基准: PRD v11 §2.2 流转表(8 态) ----------------
# (from, action) -> (to, roles, remark_required)
PRD_EDGES = {
    (None, "SUBMIT"): ("CREATED", {"EMPLOYEE"}, False),
    ("CREATED", "ACCEPT"): ("ASSIGNED", {"SUPERVISOR", "ENGINEER"}, False),  # 派单/自取
    ("ASSIGNED", "REQUEST_SUPPLEMENT"): ("PENDING_SUPPLEMENT", {"ENGINEER"}, True),
    ("PENDING_SUPPLEMENT", "SUPPLEMENT"): ("ASSIGNED", {"EMPLOYEE"}, False),
    ("ASSIGNED", "TRANSFER_EXTERNAL"): ("PENDING_EXTERNAL", {"ENGINEER"}, True),
    ("PENDING_EXTERNAL", "RESUME"): ("ASSIGNED", {"ENGINEER"}, False),
    ("ASSIGNED", "RESOLVE"): ("PENDING_ACCEPTANCE", {"ENGINEER"}, False),
    ("REJECTED", "REWORK"): ("ASSIGNED", {"ENGINEER"}, False),
    ("PENDING_ACCEPTANCE", "ACCEPT_APPROVE"): ("ACCEPTED", {"EMPLOYEE"}, False),
    ("PENDING_ACCEPTANCE", "AUTO_ACCEPT"): ("ACCEPTED", {"SYSTEM"}, False),  # 48h 超时自动通过
    ("PENDING_ACCEPTANCE", "ACCEPT_REJECT"): ("REJECTED", {"EMPLOYEE"}, True),
    ("ACCEPTED", "CLOSE"): ("CLOSED", {"EMPLOYEE"}, False),
    ("REJECTED", "CLOSE"): ("CLOSED", {"EMPLOYEE"}, False),
    ("CREATED", "CLOSE"): ("CLOSED", {"EMPLOYEE", "SUPERVISOR"}, False),  # 撤销/关重复单
    ("PENDING_SUPPLEMENT", "TIMEOUT_CLOSE"): ("CLOSED", {"SYSTEM"}, False),  # 72h 超时关闭
    ("ASSIGNED", "ABNORMAL_CLOSE"): ("CLOSED", {"SUPERVISOR"}, True),  # 异常关单
    ("PENDING_EXTERNAL", "ABNORMAL_CLOSE"): ("CLOSED", {"SUPERVISOR"}, True),
    ("PENDING_SUPPLEMENT", "ABNORMAL_CLOSE"): ("CLOSED", {"SUPERVISOR"}, True),
    ("PENDING_ACCEPTANCE", "ABNORMAL_CLOSE"): ("CLOSED", {"SUPERVISOR"}, True),
}

PRD_STATES = {
    "CREATED": "待派单", "ASSIGNED": "处理中", "PENDING_SUPPLEMENT": "待补充",
    "PENDING_EXTERNAL": "待外部", "PENDING_ACCEPTANCE": "待验收", "ACCEPTED": "已完成",
    "REJECTED": "已驳回", "CLOSED": "已关闭",
}

# Java 中文状态 → PRD 英文状态映射(用于对齐两套命名)
JAVA_STATUS_MAP = {
    "待处理": "CREATED", "处理中": "ASSIGNED", "待补充": "PENDING_SUPPLEMENT",
    "待外部": "PENDING_EXTERNAL", "待验收": "PENDING_ACCEPTANCE", "已完成": "ACCEPTED",
    "已取消": "CLOSED",
}

# Java action → PRD action 映射
JAVA_ACTION_MAP = {
    "assign": "ACCEPT", "claim": "ACCEPT", "need_info": "REQUEST_SUPPLEMENT",
    "external": "TRANSFER_EXTERNAL", "done": "RESOLVE", "supply_info": "SUPPLEMENT",
    "external_resolved": "RESUME", "accept": "ACCEPT_APPROVE", "auto_accept": "AUTO_ACCEPT",
    "reject": "ACCEPT_REJECT", "cancel": "CLOSE", "timeout": "TIMEOUT_CLOSE",
}

# Java 角色 → PRD 角色
JAVA_ROLE_MAP = {"employee": "EMPLOYEE", "engineer": "ENGINEER",
                 "supervisor": "SUPERVISOR", "system": "SYSTEM"}


def parse_java_transitions(java_path):
    """解析 Transition.java 的 TRANSITIONS Map,返回边集合。"""
    text = Path(java_path).read_text(encoding="utf-8")

    # 匹配段落起点: TicketStatus.XXX, List.of(
    starts_marker = re.compile(r"TicketStatus\.(\w+),\s*List\.of\(")
    edge_re = re.compile(
        r"Transition\.of\(\s*TicketStatus\.(\w+)\s*,\s*\"(\w+)\"\s*,\s*\"([^\"]*)\"\s*,"
        r"(?:\s*\"(\w+)\"\s*(?:,\s*\"(\w+)\"\s*)?)?\)",
    )

    # 按段落起点切分: 每段从 "TicketStatus.XXX, List.of(" 到下一段起点(或文件尾),
    # 避免非贪婪 \)\) 吞掉段内最后一条边的结尾括号导致漏解析
    starts = [(m.start(), m.group(1)) for m in starts_marker.finditer(text)]
    edges = {}
    for i, (pos, from_enum) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        body = text[pos:end]
        for em in edge_re.finditer(body):
            to_enum, action, _remark, r1, r2 = em.groups()
            roles = {JAVA_ROLE_MAP[x] for x in (r1, r2) if x}
            edges[(from_enum, action)] = (to_enum, roles)
    return edges


def main():
    parser = argparse.ArgumentParser(description="PRD v11 流转表 vs Java 实现漂移比对")
    parser.add_argument("--java", help="Transition.java 路径(默认自动定位仓库内文件)")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    # 定位 Java 文件
    java_path = args.java
    if not java_path:
        candidates = list(Path(__file__).resolve().parents[4].glob(
            "it-ticket-cloud/**/statemachine/Transition.java"))
        if not candidates:
            print("ERROR: 未找到 Transition.java, 请用 --java 指定路径", file=sys.stderr)
            sys.exit(2)
        java_path = candidates[0]

    java_edges_raw = parse_java_transitions(java_path)

    # 归一化: Java 枚举名+action → PRD 命名
    java_edges = {}
    for (from_enum, action), (to_enum, roles) in java_edges_raw.items():
        prd_action = JAVA_ACTION_MAP.get(action, action)
        java_edges[(from_enum, prd_action)] = (to_enum, roles)

    prd_keys = set(PRD_EDGES)
    java_keys = set(java_edges)

    diffs = {"missing_in_java": [], "extra_in_java": [], "target_mismatch": [], "role_mismatch": [],
             "state_enum_diff": []}

    # 1. PRD 有 / Java 无
    for k in sorted(prd_keys - java_keys, key=str):
        to, roles, _ = PRD_EDGES[k]
        diffs["missing_in_java"].append(
            f"{k[0] or '(起点)'} --{k[1]}--> {to} (角色: {sorted(roles)})")

    # 2. Java 有 / PRD 无
    for k in sorted(java_keys - prd_keys, key=str):
        to, roles = java_edges[k]
        diffs["extra_in_java"].append(
            f"{k[0] or '(起点)'} --{k[1]}--> {to} (角色: {sorted(roles)})")

    # 3. 目标态不一致 & 4. 角色守卫差异
    for k in sorted(prd_keys & java_keys, key=str):
        prd_to, prd_roles, _ = PRD_EDGES[k]
        java_to, java_roles = java_edges[k]
        if prd_to != java_to:
            diffs["target_mismatch"].append(
                f"{k[0] or '(起点)'} --{k[1]}-->: PRD={prd_to}, Java={java_to}")
        if prd_roles != java_roles:
            diffs["role_mismatch"].append(
                f"{k[0] or '(起点)'} --{k[1]}-->: PRD 角色={sorted(prd_roles)}, "
                f"Java 角色={sorted(java_roles)}")

    # 5. 状态枚举差异(以映射后的 PRD 命名对齐比较)
    prd_state_names = set(PRD_STATES)
    java_mapped = set(JAVA_STATUS_MAP.values())
    only_prd = prd_state_names - java_mapped
    only_java = java_mapped - prd_state_names
    if only_prd:
        diffs["state_enum_diff"].append(
            f"PRD 有而 Java 无的状态: "
            f"{', '.join(f'{s}({PRD_STATES[s]})' for s in sorted(only_prd))}")
    if only_java:
        diffs["state_enum_diff"].append(
            f"Java 有而 PRD 无的状态: {sorted(only_java)}")

    total = sum(len(v) for v in diffs.values())

    if args.json:
        print(json.dumps({"java_file": str(java_path), "total_drifts": total, "diffs": diffs},
                         ensure_ascii=False, indent=2))
    else:
        print("=== 状态机漂移比对报告 ===")
        print(f"基准: PRD v11 §2.2 流转表 (8 态, {len(PRD_EDGES)} 条边)")
        print(f"对比: {java_path}")
        print(f"Java 解析出 {len(java_edges_raw)} 条边")
        print(f"漂移总数: {total}")
        print()
        titles = {
            "missing_in_java": "① PRD 有 / Java 缺失的边",
            "extra_in_java": "② Java 有 / PRD 没有的边",
            "target_mismatch": "③ 目标态不一致",
            "role_mismatch": "④ 角色守卫差异",
            "state_enum_diff": "⑤ 状态枚举差异",
        }
        for key, title in titles.items():
            items = diffs[key]
            print(f"{title} ({len(items)}):")
            if not items:
                print("  无")
            for it in items:
                print(f"  - {it}")
            print()

        if total:
            print("判定: 有漂移 —— 需对齐 PRD 或走变更流程修订 PRD")
        else:
            print("判定: 一致")

    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
