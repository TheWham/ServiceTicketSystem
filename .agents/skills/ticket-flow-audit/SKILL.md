---
name: ticket-flow-audit
description: IT 服务工单流转一致性审计 Skill。两大能力：①流转日志审计——扫描 SQLite ticket_flow_log 表，检测非法流转边、越权操作、必填备注缺失、终态后操作、时间倒序、首条日志异常六类违规；②状态机漂移比对——解析 Java Transition.java 与 PRD v11 §2.2 流转表基准，输出实现漂移报告。适用于：工单数据合规审计、状态机改动后回归验证、上线前质量门禁、CI/pre-commit 集成。
---

# ticket-flow-audit —— 工单流转一致性审计

## 何时使用本 Skill

- 怀疑线上/测试库中存在**非法流转**（如终态工单被"复活"、跳状态越级操作）
- **状态机改动后**（新增状态/边/守卫）需要回归验证实现与 PRD/SPEC 是否一致
- 上线前**质量门禁**：流转日志审计通过才允许发布
- 排查"工单卡在某个状态"类工单时，先审计该工单的流转日志合法性

## 能力清单

| 脚本 | 作用 | 输入 | 退出码 |
|---|---|---|---|
| `scripts/audit_flow_log.py` | 流转日志六项审计 | SQLite 库（或 `--demo` 自检） | 0=干净 / 1=有违规 |
| `scripts/diff_state_machines.py` | PRD 流转表 vs Java 实现漂移比对 | 仓库内 Transition.java | 0=一致 / 1=有漂移 |

## 使用方式

```bash
# 1. 审计真实数据库（Node 后端 SQLite）
python scripts/audit_flow_log.py --db ../it-ticket-system/ticket.db

# 2. 无数据库时跑内置样本自检（演示检测能力）
python scripts/audit_flow_log.py --demo

# 3. CI 集成：JSON 输出 + 退出码门禁
python scripts/audit_flow_log.py --db ticket.db --json > audit_report.json

# 4. 状态机漂移比对（改完 Java Transition 后必跑）
python scripts/diff_state_machines.py
```

## 审计规则明细

### 流转日志审计（audit_flow_log.py，基准 = SPEC §3.1 十三边）

| 规则 | 检测内容 | 严重度 |
|---|---|---|
| R1 | 非法流转边：from→to 不在 SPEC §3.1 合法边集合 | CRITICAL |
| R2 | 终态后操作：ACCEPTED/CLOSED 之后仍有流转记录 | CRITICAL |
| R3 | 首条日志异常：工单首条流转不是 (起点)→CREATED | HIGH |
| R4 | 必填备注缺失：REQUEST_SUPPLEMENT / TRANSFER_EXTERNAL / ACCEPT_REJECT 边 remark 为空 | HIGH |
| R5 | 时间倒序：同一工单内 created_at 非递增 | MEDIUM |
| R6 | 越权操作：operator 角色不在边的允许角色集（SUPERVISOR 全局放行） | CRITICAL |

### 状态机漂移比对（diff_state_machines.py，基准 = PRD v11 §2.2 流转表）

- 边集合差异：PRD 有 / Java 无、Java 有 / PRD 无
- 目标态不一致：同一 (from, action) 两边目标状态不同
- 角色守卫差异：同一边允许角色集合不同
- 状态枚举差异：状态数量与命名（Java 中文 7 态 vs PRD 英文 8 态）

## 判定标准

- 日志审计：任一 CRITICAL/HIGH 违规 → 退出码 1，禁止发布
- 漂移比对：任何一类差异 → 退出码 1，必须先对齐 PRD 或走变更流程修订 PRD

## 维护纪律（重要）

1. **基准单一来源**：SPEC §3.1（`acceptance/src/ticket_p0/state_machine.py`）与 PRD v11 §2.2 是两份基准，改状态机必须三方同步（PRD → SPEC → Java），改完必跑 `diff_state_machines.py`
2. 本 Skill 的边定义与 SPEC 同源，SPEC 变更时同步更新 `audit_flow_log.py` 中的 `EDGES` 常量
3. 审计脚本只读不写，可安全对生产库快照执行；生产审计建议用 `sqlite3 db ".backup"` 先做快照
