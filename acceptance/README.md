# IT 服务工单系统 —— 工具链受控代码生成与验收跑测（提单链路）

> 培训作业「步骤3」交付物：以《验收评测协议书 V2》与《技术SPEC规格书 V1.1》为输入，
> 通过 `.cursorrules` 受控生成核心实现，测试集先行（tests/test_service.py），pytest 全绿后回放验收。
>
> 覆盖范围对齐 V2 §4.1-1：提单链路（M-01~M-09、TC-01~TC-10，权重合计 48%）；
> 回放报告按 V2 §2.1 **全量 16 项**列示，M-10~M-16 标明阈值与回填责任方。
> V2 变更点已落地：TC-07 改为「描述为空·必填缺失」、description 取消 10 字下限（保留 500 上限）、
> M-06 幂等拦截码 40901、指标权重更新（8/4/8/6/6/6/5/3/2）、门禁一律 100% + 零容忍项 + 加权得分仅用于质量分级。
> M-10~M-16 由 ticket/consultation 集成测试与 evals/golden_datasets 金标回放另行覆盖。

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
│   └── test_service.py     #   质量负责人测试集：TC-01~10 + M-01~09 + 状态机/守卫/超时（27 项，V2 口径）
├── scripts/run.py             # V2 §4.1-1 自动化回放：执行记录表 + 16 项指标汇总 + §4.2 综合判定
└── reports/验收评测执行记录-实测.md
```

## 文档

- [docs/验收测试设计说明.md](docs/验收测试设计说明.md)：测试生成机制、运行方式、27 项用例详解与 16 项指标映射

## 运行方式

```bash
cd it-ticket-p0-acceptance
python -m pip install pytest        # 已装可跳过
python -m pytest -v                 # 大屏展示：27 passed（100%）
python scripts/run.py               # 生成《验收评测执行记录-实测.md》
```

## 文档 → 代码 → 测试 对照

| 协议书/SPEC 条款 | 实现 | 测试 |
| :--- | :--- | :--- |
| §3.1 TC-01~05 正向五分类 | validation + submit | test_tc01~05（TC-01 含 M-03 逐字段比对） |
| V2 §3.1 TC-06 标题必填 / TC-07 描述为空必填（V2 变更样本） | validate_submission | test_tc06 / test_tc07 |
| V2 §3.1 TC-08/09 临界边界（title 50/2位 vs 51/501/5位/过去时间） | 长度与正则阈值 | test_tc08 / test_tc09（四字段独立报错） |
| §3.3 TC-10 四向量注入 | XSS 拒绝 / 参数化 SQL / 资产正则 / MIME 魔数 | test_tc10 |
| V2 §2.1 M-01~M-09 门禁一律 100%（M-06/M-08 为零容忍项，M-06 拦截码 40901） | 对应服务链路 | test_m01 / m05 / m06 / m07 / m08 / m09 |
| SPEC §3 状态机 13 边 + 守卫 | state_machine.EDGES + transit | test_state_machine_* / test_guard_* / test_terminal_* |
| SPEC §2.1 T2/T3 超时只告警不改状态 | scan_timeouts（60s 幂等） | test_timeout_T2_* / test_timeout_T3_* |
| SPEC §1.6 发号 / §2.2-3 草稿 | _next_ticket_id / ticket_draft | test_ticket_id_* / test_draft_* |

## 实测结论（2026-10-08 回放，V2 口径）

- pytest：**27 passed（100%）**
- 验收回放：TC-01~TC-10 全部符合预期；M-01~M-09 逐项 100% 达标（V2 确定性门禁）；
  零容忍项（TC-10 / M-06 幂等 40901 / M-08 MIME 校验）无违反；综合判定（V2 §4.2）：**通过**
- 加权得分：覆盖范围 **48/48**（M-01~M-09 权重合计 48%；V2 质量分级 ≥98 优秀 / 95~98 良好，
  仅用于分级，不替代逐项判定）
- M-04 说明：单测仅覆盖 M-04b 进程内采样（P95=0.36ms / P99=0.42ms）；V2 四子项综合按
  `0.25×(04a+04b+04c+04d 达标数)` 计，04a/04c/04d 以前端埋点与 AI 链路实测为准（V2 §2.2.4）
- 范围外：M-10~M-16（权重 52%）由 ticket-service/consultation-service 集成测试与
  `evals/golden_datasets` 金标回放回填后形成整体验收终判
