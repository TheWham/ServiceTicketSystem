# IT 服务工单系统 P0 —— 工具链受控代码生成与验收跑测

> 培训作业「步骤3」交付物：以《验收评测协议书》（步骤1）与《技术SPEC规格书 V1.1》（步骤2）为输入，
> 通过 `.cursorrules` 受控生成核心实现，测试集先行（tests/test_service.py），pytest 全绿后回放验收。

## 工程结构

```
it-ticket-p0-acceptance/
├── .cursorrules            # 受控代码生成约束（8 章铁律：错误码/校验/状态机/幂等/安全/禁止事项）
├── pytest.ini
├── src/ticket_p0/          # SPEC → 代码 的映射实现（仅标准库）
│   ├── constants.py        #   SPEC §1.8 枚举 / §1.7 阈值 / §2.1 超时 / §2.7 错误码
│   ├── errors.py           #   BizError + ValidationFailed（多字段错误一次性返回）
│   ├── clock.py            #   SystemClock / FixedClock（3s 幂等窗、2h 超时确定性测试）
│   ├── storage.py          #   SQLite 7 表（§1.1~§1.6），全参数化 SQL
│   ├── attachment.py       #   魔数嗅探（JPEG=FFD8FF / PNG=89504E47），防 EXE 伪装
│   ├── validation.py       #   §1.7 七字段校验矩阵
│   ├── state_machine.py    #   §3.1 十三合法边 + Guard（角色/本人/remark/乐观锁）
│   └── service.py          #   submit / transit / scan_timeouts / recommend_safely / 草稿
├── tests/
│   ├── conftest.py         #   夹具：FixedClock(2026-09-21 12:00) + CMDB 种子（§六-1）
│   └── test_service.py     #   质量负责人测试集：TC-01~10 + M-01~09 + 状态机/守卫/超时（27 项）
├── scripts/run_acceptance.py  # §4.1 自动化回放：填充 §4.2 记录表 + §4.3 汇总表 + §5.1 判定
└── reports/验收评测执行记录-实测.md
```

## 运行方式

```bash
cd it-ticket-p0-acceptance
python -m pip install pytest        # 已装可跳过
python -m pytest -v                 # 大屏展示：27 passed（100%）
python scripts/run_acceptance.py    # 生成《验收评测执行记录-实测.md》
```

## 文档 → 代码 → 测试 对照

| 协议书/SPEC 条款 | 实现 | 测试 |
| :--- | :--- | :--- |
| §3.1 TC-01~05 正向五分类 | validation + submit | test_tc01~05（TC-01 含 M-03 逐字段比对） |
| §3.1 TC-06/07 必填与下限 | validate_submission | test_tc06 / test_tc07 |
| §3.2 TC-08/09 临界边界（50/10/2位 vs 51/501/5位/过去时间） | 长度与正则阈值 | test_tc08 / test_tc09（四字段独立报错） |
| §3.3 TC-10 四向量注入 | XSS 拒绝 / 参数化 SQL / 资产正则 / MIME 魔数 | test_tc10 |
| M-01 ≥98% / M-05 ≥99.5% / M-06 100% / M-07 100% / M-08 / M-09 | 对应服务链路 | test_m01 / m05 / m06 / m07 / m08 / m09 |
| SPEC §3 状态机 13 边 + 守卫 | state_machine.EDGES + transit | test_state_machine_* / test_guard_* / test_terminal_* |
| SPEC §2.1 T2/T3 超时只告警不改状态 | scan_timeouts（60s 幂等） | test_timeout_T2_* / test_timeout_T3_* |
| SPEC §1.6 发号 / §2.2-3 草稿 | _next_ticket_id / ticket_draft | test_ticket_id_* / test_draft_* |

## 实测结论（2026-09-21 回放）

- pytest：**27 passed in 5.51s（100%）**
- 验收回放：10/10 样本符合预期；M-01~M-09 全部达标；加权得分 **100%**；§5.1 判定：**通过**
- M-04 说明：单测为进程内采样（P95=8.19ms），仅演示埋点口径；生产 P95/P99 以 E2E 埋点为准
