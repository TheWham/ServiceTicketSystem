# 单库初始化与存量升级

唯一运行库名是 `it_ticket_system`。依据 `docs/IT服务工单系统PRD-Ultimate.md` 2.2、DM 与 SQL 规范，并遵守本次用户追加范围：**只对齐已经实现的模块，未开发模块运行字段不动**。

## 空库

`init/00-schema.sql` → `init/10-seed.sql` → `init/11-knowledge-seed.sql`。
Docker 仅对新数据目录执行这些文件。已有安装不得重跑 seed 或把初始化脚本当升级脚本。共 34 张表：26 张实际实现模块表按规范对齐，8 张保留 main 原结构；不是 SQL-009 的全部 41 表发布制品。新增的 6 张已使用表为 `engineer_runtime_state`、`engineer_category_capability`、`service_calendar`、`calendar_holiday`、`idempotency_record`、`outbox_event`。

种子统一用户 `U_EMP01/U_ENG01/U_ADM01/U_KBA01`、分类 `C_HW_PC/C_HW_PR/C_SW/C_NET/C_ACC/C_OTH`（另有父分类 `C_HW`），知识管理员角色为 `KNOWLEDGE_ADMIN`。知识和工程师路由引用这些同一批 ID。默认服务日历 `DEFAULT`，`Asia/Shanghai`，09:00–12:00 / 13:00–18:00；没有猜测节假日。日期时间事实统一 UTC。

## main 388f51d 存量升级

仅供这一已冻结的 main 28 表结构。未知结构须先做差异审核；不能在旧 `it_user/it_ticket/it_consultation` 三库直接执行。脚本不在应用启动或 Docker init 时运行，也没有连接或修改任何实际业务库。

1. 备份并完成恢复演练，先在恢复副本执行。停止所有旧应用写入，并一直维持到切换后；脚本不提供 CDC。确认旧 main DATETIME 的实际时区。原默认是 `Asia/Shanghai`，部署可能覆盖，不能默认为 UTC。
2. 在同一 MySQL 会话显式设置 `@migration_operator` 为真实操作人、`@main_writes_stopped=1`、`@main_source_utc_offset` 为已核对的源偏移，例如 `'+08:00'`。偏移必须适用于全部待迁移历史时刻；跨夏令时历史必须另写按记录转换的适配器。不要从新服务 UTC 配置反推旧数据时区。
3. 用 **遇错即停** 的版本化 SQL runner 执行 `migration/V2_0__stage_main_canonical.sql`。MySQL CLI 不得加 `--force`。脚本先报告 `migration_v2_issue`，再建显式 `v2_stage_*` 表并在一个事务复制；未知枚举、孤立引用、重复活动草稿、无法恢复的 SLA 或历史工作日历会阻止迁移。禁止通过删业务记录绕过门禁。
4. 检查报告、行数、UTC 转换、身份与角色、消息正文、审计内容、RAG 当前版本和业务抽样。此阶段目标是冻结的 470ce57 中间结构，不是当前规范；用 `tests/fixtures/canonical-470ce57-schema.sql` 核对。未开发表必须与 main 原结构一致。
5. 同一维护窗口、同一组显式参数执行 `migration/V2_1__cutover_main_canonical.sql`。再次检查源/目标行数后，一条 `RENAME TABLE` 原子切换 26 张目标表；20 张被替换源表保留为 `legacy_v1_*`。8 张暂缓模块原表不改名、不改列、不复制。继续按下节执行 V2_2，完成最新元数据验证后才能启动本次应用；旧表只用于核对与恢复，不再是运行事实源。
6. `schema_migration_audit` 保存版本、结构摘要、操作人、源时区和时间。已经成功的版本不得重跑；迁移 runner 依据版本记录跳过。失败复制事务会回滚，但 DDL 会保留 staging/例程和诊断表；将报告归档，在新的恢复副本修订转换器后重试。不要用破坏性的“清理整个库”恢复。元数据切换与后续审计插入不是同一事务；若连接恰在其间中断，先检查 `legacy_v1_*` 和当前表，再补偿审计，不能直接重放切换。

以下存量不会被悄悄猜测：

- `sla_instance` 有任意旧记录：缺少历史目标工作秒、日历版本和 `STOPPED` 的确切含义，需提供经审核的 SLA 转换适配器。当前脚本报告并阻断，因此不能声称所有生产数据已经可自动迁移。
- `work_calendar` 有任意记录：旧逐日工作时段/午休需要审核如何表示为版本日历；原表完整保留，运行迁移暂阻断。旧表为空时可采用 PRD 默认日历。
- `ticket_transition.event` 原代码曾用目标状态小写，无法可靠反推业务动作。迁移为 `LEGACY_<原值大写>`，保留原表，不伪装成新领域动作；后续新写使用规范动作码。
- 旧 `audit_log` 文本包装成 `{"legacyText": ...}`，原本有效 JSON 保持 JSON。缺失 request ID 使用明确的 `legacy-main-audit-<id>`；数字审计 ID转字符串保留原值。
- 已解决/已关闭时间仅复制可证实的原时间；不会编造完整解决、验收或评价历史。

## 470ce57 到 PRD 2.2 统一字段：V2_2

目标包含 a99ab6a 的规范修订及用户随后确认的 PRD 2.2 字段统一，不仅是 a99ab6a 原提交；源版本声明仍固定为 470ce57。

已发布的 V2_0/V2_1 文件与含义不变，生成器读取冻结 470ce57 fixture；SHA-256 固定在契约测试与 spec11。470ce57 空库安装或已完成 V2_1 的实例都直接执行新增 `V2_2__align_prd_field_names.sql`，不重跑旧迁移或 seed。

1. 在恢复副本核对冻结源结构，备份并停止写入。在执行会话中设置 `@main_writes_stopped=1`、非空 `@migration_operator` 和 `@canonical_source_revision='470ce57'`；最后一个参数是已核对源版本的显式声明，不是跳过结构检查。
2. 用遇错即停的 runner 执行 V2_2。源列不匹配、目标 user 已存在、未知 enabled 值、非法 SLA 业务关联、重复执行均阻断。合法 enabled 仅 0/1，映射到 DISABLED/ACTIVE。
3. 12 张变更表复制到 `v2_2_stage_*` 并检查行数，再一次原子切换；源表保留 `legacy_v2_*`。其他表（包括未开发 8 表）不变。时间直接复制，绝不将 470 的 UTC 再减 8 小时；JSON、版本、动作/结果/反馈枚举原样保留。SLA 的 TICKET 记录补 ticket_id=biz_id，CONSULTATION 记录为空；知识全文投影从 content JSON 重建。
4. 执行 `tests/verify-canonical-metadata.sql` 应返回零行。核对身份状态、微秒时间、JSON、业务 ID、索引、行数与源表抽样，再启动应用。迁移辅助表/历史表不算当前 34 张业务表。
5. 切换后审计插入若因断连失败，必须先查当前表与 `legacy_v2_*` 再恢复；DDL 与审计不是一个事务，不能盲目重跑。失败 staging 保留，不自动清空数据库。成功版本由 `schema_migration_audit` 记录并禁止重放。

本目录提供脚本与隔离验证，不授权或自动执行真实业务数据库迁移。

## 旧三库数据迁移边界

本次只交付 main 单库结构升级。旧分支三库的数据合并 **不自动运行**，也不把拆库 seed 的 `U004/U005/U006` 或 `CAT-IT-*` 偷换成现有人员/分类：这些可能是真实不同主体。

若需导入三库数据，必须单独制作并审核导出、冻结的身份/分类/ID 映射表、源时区标识、冲突报告和重放批次。先只读导出到 staging，分别处理旧 ticket 中文枚举/字段、consultation UTC 时间、同名共享表冲突、知识版本指针和业务 ID 碰撞，验证计数、引用和审计后才另行切换。未知映射阻断导入，源库和原导出保持不变。本目录没有自动连接三库、TRUNCATE 或静默覆盖业务行的脚本。

## 生成与验证

在仓库根目录：

```powershell
python it-ticket-cloud/db/tools/build_schema.py
python it-ticket-cloud/db/tools/build_migration.py
python it-ticket-cloud/db/tools/build_latest_migration.py
python it-ticket-cloud/db/tools/validate_schema.py --emit-sql it-ticket-cloud/db/tests/verify-canonical-metadata.sql
python -m unittest discover -s it-ticket-cloud/db/tests -p 'test_*.py'
```

真实 MySQL 验证仅对调用者启动的本机隔离实例使用：

```powershell
python it-ticket-cloud/db/tests/run_mysql_validation.py --mysql <mysql.exe绝对路径> --port <隔离端口> --report <报告路径>
```

测试固定连接 `127.0.0.1`，不读取应用/远程配置，不选择业务数据库；每轮创建唯一 `schema_test_*` 临时库。测试覆盖全量建表/seed、元数据/唯一键、ngram 检索、388→V2_0/1/2、470→V2_2、UTC/微秒保留、SLA 双业务关联、知识/AI/审计 JSON、动作/结果枚举、未开发表保持、缺时区/未知枚举/缺 SLA 依据/停写后行数漂移/重放阻断。`tests/fixtures` 是冻结历史结构与 seed，禁止挂进初始化目录。
