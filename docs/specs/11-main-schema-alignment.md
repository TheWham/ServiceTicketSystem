# main 与 PRD 字段对齐及单库升级范围

## 2026-09-30 当前裁定：两套初始化完整 41 表

用户明确要求根目录 SQL 和运行 `db/init` 一起强对齐完整 PRD/spec，替代下方历史记录中的“未开发 8 表不动”初始化范围。

- `db/it_ticket_system_init_v2.sql` 与 `it-ticket-cloud/db/init/00-schema.sql` 均由 `it-ticket-cloud/db/tools/build_schema.py` 从 SQL-007/010 生成同一套 41 表；根目录文件还拼入运行目录的两份种子脚本。两个入口只能选一个用于空库。
- 附件、案例、知识簇、工单消息、动态字段全部采用完整规范。旧 `category_field_def` 改由 `field_definition` 表达，旧 `work_calendar` 改由 `service_calendar/calendar_holiday` 表达；规范未列出的 `engineer_status_log` 不在新空库创建。旧库的数据没有被删除或自动转换。
- 已记录的兼容字段继续作为实现投影：`user.password_hash`；工单分类、影响/紧急、资产校验、幂等、响应/解决/评价字段；草稿明细投影；SLA 提醒字段；通知和异常展示字段；`knowledge_version.search_text` 及全文索引。规范字段仍是事实来源，知识搜索投影从 `content JSON` 生成。
- 各表统一创建/更新时间；补齐 DM 要求的分配唯一键、provider 唯一 ACTIVE 配置。枚举 CHECK 来自 DM-002/004，SLA 双业务关联由 CHECK 校验。附件读取仅返回 `PASSED` 且未撤回记录。
- 完整建模不等于完成全部业务功能，不扩展尚未实现的 API。
- `V2_0/V2_1/V2_2` 保持原字节与含义；V2_2 生成器改读冻结的 `tests/fixtures/canonical-prd22-34-schema.sql`。这条历史链只到 34 表版本，不能作为本次 41 表升级方案。存量库须单独审核字段/JSON/枚举/数据映射与新增迁移后才能切换应用。
- 当前元数据门禁检查 41 表；历史迁移验证读取冻结 34 表 fixture，不能用新标准改写历史测试目标。

以下内容均为 2026-09-29 及更早的范围、实现与验证历史；其“当前”“本轮”描述属于对应历史版本，不覆盖本节。

## 当前裁定：PRD 2.2 业务名称优先，规范补充类型和技术字段

本节替代下方 470ce57 历史记录中的字段裁定。用户在 a99ab6a 更新规范后，进一步要求整套 PRD/spec 强对齐；不能继续把旧 SQL 名称当作业务命名权威。已实现模块按 PRD 第 20 节业务字典同步运行 DDL、Java、查询、DTO 与 OpenAPI。技术字段、UTC/DATETIME(6)、强类型、版本与索引继续由 DM/SQL 补充。

当前运行表仍为 **34 张：26 张已实现模块表 + 8 张未开发 main 原表**。身份表现在是 `user`，没有新增身份实体；本次没有把 SQL-009 的完整 41 表模板全部发布。

本轮最终应用验证：后端 **221** 项、前端 **41** 项、文档一致性 **5** 项、SQL静态 **10** 项测试通过，后端打包/前端构建通过。三个业务服务与网关在独立本机端口连接临时库，验证完整用户投影、禁用账号、分类、草稿互通、工单幂等与转单回调、SLA、通知、知识JSON检索、AI审计和咨询结果。禁用工程师即使保留 AVAILABLE 在线状态，也不能被普通分配或恢复咨询选中；用户服务失败时工单路由不放行未知状态候选。该验证不代表现有业务数据库已执行升级。

运行范围依据当前父 POM、网关路由和前端路由确定。`60be231` 合入的独立 `ai-service`、`AiChatPanel.vue`、`AgentWorkbenchView.vue` 尚未接入当前 reactor/主路由；本轮保留这些业务代码，不自动启用第二套聊天或知识表。唯一配置清理是移除此前提交中两处明文 API key 默认值，保留原环境变量名；历史泄露凭据需另外撤销更换，不能仅靠改文件消除历史。当前运行的 AI/人工咨询仍由 `consultation-service` 承担。

| 对象 | 470ce57 已发布字段 | 当前 PRD/规范与 V2_2 处理 |
|---|---|---|
| 身份 | `user_account.display_name/enabled` | `user.name/status`；1→ACTIVE、0→DISABLED；保留 ID、密码哈希、版本与时间 |
| 支持组与成员 | `enabled` | `status VARCHAR(32)`；1→ACTIVE、0→DISABLED |
| 分类 | `nature/enabled` | `ticket_nature/status`；能力表的 `enabled` 保持技术布尔字段 |
| 工单 | `ticket_nature/field_snapshot_json` | `nature/field_definition_snapshot JSON` |
| 草稿 | `nature` | `ticket_nature`；JSON 载荷与兼容投影保持 |
| 咨询 | `resolution_type` | `resolved_type`；已规范化的枚举值不变 |
| 工单流转 | `event_code` | `event`；仍保存领域动作码，历史 `LEGACY_` 不伪装成新动作 |
| SLA | `breached_at`、仅通用业务关联 | `breach_at`；新增可空 `ticket_id`，TICKET 时等于 biz_id，CONSULTATION 时为空；通用 biz_type/biz_id 保留 |
| 知识版本 | `content_json` | `content JSON`；search_text 从该列重新生成，保留 ngram 全文索引 |
| AI 审计 | `retrieved_versions_json/latency_ms` | `retrieved_versions JSON/latency BIGINT`；引用数组、反馈、置信度与耗时值保留 |
| 业务审计 | `before_json/after_json` | `before_value/after_value JSON`；保持 JSON 原值 |

未开发运行表 `attachment,case_candidate,category_field_def,engineer_status_log,knowledge_cluster,ticket_field_value,ticket_message,work_calendar` 的 DDL 逐字保持 main-388f51d 快照。spec06 中附件 `file_name/size/hash`、案例 `structured_content JSON`、动态字段 `field_definition_snapshot/field_value JSON` 是未来模板；本次不改这些运行表的列、类型、枚举或数据。

## 新增升级版本及历史不可变性

- 空库直接执行当前 `db/init`，不执行历史升级。
- 388f51d 安装：按顺序执行冻结的 `V2_0 → V2_1` 到 470ce57，再执行新增 `V2_2__align_prd_field_names.sql`。
- 已部署 470ce57 安装：仅执行 V2_2，不重跑 V2_0/1，不重新初始化或 seed。
- V2_0/V2_1 生成器只读取冻结的 `tests/fixtures/canonical-470ce57-schema.sql`，不再读取当前可变 spec。原 main schema/seed 与 470 schema/seed 均保留测试快照。
- V2_2 要求停写、实名操作人和显式 `@canonical_source_revision='470ce57'`。它检查源列和状态值，将 12 张变更表复制到独立 staging，校验行数后一次原子换名；源表保留为 `legacy_v2_*`，其余表完全不替换。未知 enabled 值或非法 SLA 关联阻断，不猜测、不丢数据、不再次转换 UTC。
- 切换 DDL 与审计插入并非同一事务；若切换后断连，先核对当前/legacy 表及审计再恢复，不能直接重放。失败时保留诊断和 staging，在恢复副本审核后处理。

历史文件 SHA-256（契约测试强制验证，禁止无声重写）：

| 文件 | SHA-256 |
|---|---|
| V2_0__stage_main_canonical.sql | `879ec56a246664d373808d9286e0550bfb28a2641856705a39243da5f3c70848` |
| V2_1__cutover_main_canonical.sql | `59a2dc7690f507ab9a1ad1746bbb00d2044e8fcbf65047537d4c3bd429bfe308` |

验证命令及恢复边界见 `it-ticket-cloud/db/README.md`。验证只使用本机隔离 MySQL 8.0.43 的新 `schema_test_*` 库；运行测试不意味着真实业务数据库已经执行升级。

2026-09-29 本轮验证：静态契约 **10/10** 通过，重新生成 V2_0/1 后历史 SHA-256 不变；独立 MySQL **11 组**通过。覆盖当前 34 表/seed/元数据/全文搜索、388 完整升级链、470 直接升级、12 张源表保留、UTC 微秒与版本、ACTIVE/DISABLED、SLA 双业务关联、业务动作/咨询结果/AI 反馈枚举、知识/AI/审计 JSON，以及缺时区、未知枚举、缺 SLA 依据、行数漂移和成功版本重放阻断。未开发 8 表在离线 DDL 和真实 MySQL SHOW CREATE TABLE 两层均验证保持不变。

## 历史记录：470ce57 裁定与当时的验证

以下保留上一轮合并的差异证据与验证事实；其中 `user_account/enabled/content_json` 等字段描述仅适用于 470ce57 中间版本，当前命名以上方新裁定为准。它们仍是冻结 V2_0/1 的合法目标，不应为迎合新规范改写历史迁移。

对比基线：`origin/main` 提交 `388f51d`；功能分支 `feature-aicutomer` 提交 `6b14efb`。最终运行数据库为项目现有 SQL 名 `it_ticket_system`。本记录服从用户最后追加要求：**还没写的功能模块的字段暂时先不动**。

## 权威与证据

- 根目录 `IT服务工单系统PRD-Ultimate.md` 是 **2.0，2026-09-28**；`docs/IT服务工单系统PRD-Ultimate.md` 是 **2.1，2026-09-29**。本次以 docs 2.1 及 `01-data-model-strong-types.md` / `06-mysql-ddl-and-migrations.md` 为字段与枚举权威，HTTP 使用 `05-http-api-openapi.yaml`。
- `DM-004 Ticket.nature` 是 Java 领域属性；实际 SQL-007 列名明确为 `ticket_nature`；`category.nature` 与草稿 `nature` 仍按 SQL-010。避免将领域属性名误当每张表的列名。
- 原 main DDL/seed 已冻结在 `it-ticket-cloud/db/tests/fixtures/main-388f51d-{schema,seed}.sql`，供测试核对。原 28 张表并非 SQL-009 的全表实现。
- 本次实际代码依据为 ticket/user/consultation 的 `@TableName`、Mapper SQL 与服务调用；知识的 `KnowledgeQueryMapper` 已实际使用 `knowledge_article/knowledge_version.content_json/search_text`。附件只有工单列表读取，未实现上传、扫描和下载全流程。
- 生成器维护显式 `IMPLEMENTED` 集合；验证器对其余原 main 表做 DDL 逐字比较，防止借对齐之名扩展未开发模块。

## 最终范围：34 张表，而非补齐全部 41 张规范表

26 张当前实现模块表对齐规范字段：

`user_account,user_role,support_team,team_member,engineer_runtime_state,engineer_category_capability,category,category_route,consultation,consultation_message,ticket,ticket_transition,ticket_draft,assignment,sla_instance,sla_pause,service_calendar,calendar_holiday,exception_queue,notification,audit_log,idempotency_record,outbox_event,knowledge_article,knowledge_version,ai_interaction`。

8 张原 main 表原结构保留：

`attachment,case_candidate,category_field_def,engineer_status_log,knowledge_cluster,ticket_field_value,ticket_message,work_calendar`。

相对 main 新增 **6** 张已经被服务使用的表：工程师在线/能力、服务日历/假日、幂等、Outbox。`user` 改名统一为 `user_account` 不算额外实体。

以下原来没有、尚未实现模块的表 **不新建**：`field_definition,supplement_request,external_wait,ticket_resolution,ticket_acceptance,ticket_duplicate,attachment_access,outbox_delivery,ai_provider_config,rag_index_pointer`。原有 `ticket_field_value/ticket_message/attachment/case_candidate/knowledge_cluster` 也不因 SQL-009 清单而扩展。本次不是全 PRD 功能完成或 41 表全量发布。

## 本次已实现模块：main 原定义 → 规范 → 处理

| 对象 | main 原定义 | DM/SQL 规范 | 本次处理/迁移 |
|---|---|---|---|
| 身份表 | `user` | `user_account` | 统一新表与实体；原表留存 |
| 用户姓名/启用 | `name VARCHAR(64)` / `status ACTIVE` | `display_name VARCHAR(255)` / `enabled` | 名称映射，ACTIVE/DISABLED显式转换 |
| 用户组织 | 可空 `department_id` | 非空 VARCHAR(64) | 空组织报告并阻断，不猜部门 |
| 用户同步/锁 | 无同步时间、version | `last_identity_sync_at` / BIGINT version | 实际身份模块补列，版本从0开始 |
| 角色键/角色值 | 自增 id、非唯一 `(user_id,role_code)`、`KB_ADMIN` | 复合主键、`KNOWLEDGE_ADMIN` | 角色改规范；重复历史授权阻断而非丢弃 |
| 团队 | `status ACTIVE`、无version | `enabled`、BIGINT version | 状态映射、补版本 |
| 团队成员 | 自增id/status | `(team_id,engineer_id)` PK、enabled、left_at | 唯一成员关系，重复关系由约束阻断 |
| 分类性质 | `ticket_nature VARCHAR(20)` | `nature VARCHAR(32)` | 按分类规范改名 |
| 分类配置 | status、name64、level tinyint、version int | enabled、name255、level smallint、definition_version、version bigint | 旧定义版本明确记为 `legacy-main-v1` |
| 路由 | 自增id、普通分类/顺序索引 | `(category_id,team_id,effective_at)` PK；`(category_id,route_order,effective_at)` UNIQUE；expired_at | 保留生效时刻，补过期/更新时间，唯一冲突阻断 |
| 工单性质 | `nature VARCHAR(20)` | `ticket_nature VARCHAR(32)` | Java属性保留nature时显式列映射 |
| 工单正文 | `description VARCHAR(5000)` | TEXT | 不截断原值；HTTP仍按spec长度校验 |
| 工单影响/紧急 | VARCHAR(500) | TEXT；HTTP上限2000 | 对齐存储/API长度 |
| 工单地点/联系方式 | VARCHAR(200)/VARCHAR(64) | VARCHAR(255)/VARCHAR(255) | 扩容，保留原值 |
| 工单人员/分类ID | VARCHAR(32) | VARCHAR(64)，ticket_id仍32 | 仅扩宽，不重新生成ID |
| 工单快照 | 无 `field_snapshot_json` | JSON | 实际建单已使用，补列；不改未实现field_value模块 |
| 工单完成时间 | `solved_at`；无completed/closed | `completed_at/closed_at DATETIME(6)` | solved_at可证实值映射completed_at，旧UI列保留；不伪造关闭事件 |
| 工单版本/索引 | int；creator+created，缺priority/status | BIGINT；creator/status、assignee/status、priority/status | 增加规范索引及title/category/created查询索引 |
| 草稿所有者 | `user_id`普通索引 | `creator_id`唯一 | 同员工多草稿先报告，不静默选一条 |
| 草稿载荷 | 分散明细列，无JSON | `payload_json JSON` | 旧明细转换为明确JSON快照；实际UI兼容列保留 |
| 草稿保存/过期/版本 | 仅updated_at | last_saved_at/expires_at/version/created_at | 保存时间从原updated_at来，过期=原保存+7天，nature REQUEST→SERVICE_REQUEST |
| 工单流转事件 | `event`，原代码写目标状态小写 | `event_code VARCHAR(64)`动作码 | 新写规范动作；历史`LEGACY_<原值>`，不虚构动作 |
| 工单流转顺序 | ticket/time普通索引 | ticket/time/transition唯一排序键 | 按规范建键；历史正文保留 |
| 咨询来源 | `DIRECT_HUMAN` | `HUMAN_DIRECT` | 显式枚举转换 |
| 咨询解决/关联 | `resolved_type CONFIRMED/AUTO`、`ticket_id`、auto_resolved | `resolution_type EMPLOYEE_CONFIRMED/AUTO_RESOLVED`、`converted_ticket_id` | 显式转换；原投影留源表用于核对 |
| 咨询关闭/锁 | 无 closed_at/version | closed_at / BIGINT version | 已关闭记录使用已存在updated_at作为旧关闭投影来源；新写规范字段 |
| 咨询消息 | 无client_message_id/citation/sent_at/withdraw_reason | 对应字段、MEDIUMTEXT、会话/客户端消息唯一 | 历史client ID明确`legacy-<message_id>`，sent_at从created_at来 |
| assignment | ID32，缺updated_at；TIMEOUT_TRANSFER/TRANSFER_APPLY | ID64、updated_at；TIMEOUT/TRANSFERRED | 保留同一biz_type/biz_id事实，枚举显式映射 |
| SLA业务归属 | ticket_id专用 | biz_type/biz_id支持TICKET/CONSULTATION | 两服务共用一份SLA模型 |
| SLA类型/违约 | RESPONSE/COMPLETION、breach_at、STOPPED | TICKET_RESPONSE/TICKET_COMPLETION/CONSULTATION_RESPONSE、breached_at、MET等 | 新写规范；旧SLA非空时需审核适配器，不能猜STOPPED含义 |
| SLA目标/日历 | 缺目标工作秒、日历ID/版本、met_at、version | 对应canonical字段 | 新实现写全；历史依据缺失阻断迁移 |
| SLA暂停 | SUPPLEMENT/EXTERNAL，无created/updated | PENDING_SUPPLEMENT/PENDING_EXTERNAL，审计时间 | 显式转换，时间从started/ended来 |
| 运行日历 | work_calendar逐日表 | service_calendar/calendar_holiday | 已实现服务改读版本日历；旧表不改，非空转换需reviewed adapter |
| 通知渠道 | INBOX | IN_APP | 显式映射，EMAIL保留 |
| 通知状态/时间 | 缺sent_at/read_at、字段长度偏小 | 规范字段与长度 | 实际通知读写补列；不能恢复旧发送时刻就保持NULL |
| 异常队列 | biz_type/biz_id/exception_type/resolution | object_type/object_id/reason_code/reason，claimed_by/at，开放异常唯一键 | 字段映射，重复事实阻断；展示扩展保留 |
| 审计主键 | BIGINT AUTO_INCREMENT | VARCHAR(64)业务ID | 数字ID转字符串原值，新写业务ID |
| 审计前后值 | before_value/after_value TEXT | before_json/after_json JSON | 有效JSON原值保留；纯文本包装legacyText |
| 审计追踪 | request_id可空、occurred_at秒级 | request_id必填、DATETIME(6)、created/updated | 缺失追踪标识明确legacy来源，不伪称原HTTP请求 |
| 已发布知识文章 | category可空、无version | category非空、version BIGINT | 真实RAG查询依赖；无分类历史需审核 |
| 已发布知识版本 | title/content分列、recheck_by、非唯一版本索引 | content_json、platform_reviewer_id、唯一article/version、平台复核字段 | title/body转JSON；旧复核人映射，不能推断的决定/时刻NULL；增加可重建search_text/ngram |
| AI审计 | retrieved_versions VARCHAR500、latency int、confidence(4,3)、UNHELPFUL/WRONG | retrieved_versions_json JSON、latency_ms BIGINT、confidence(8,4)、NOT_HELPFUL/INCORRECT | 有效引用JSON复制；非法JSON阻断；旧answer留源表，不新增到规范元数据 |
| 幂等/Outbox | main无表 | idempotency_record/outbox_event | consultation已有真实事务读写，补表；不扩展未实现delivery表 |
| 时间/枚举通则 | 秒级DATETIME、短VARCHAR；main默认本地时间 | 范围内DATETIME(6)/UTC、枚举VARCHAR32 | 仅实现范围统一；升级要求显式源UTC偏移，未知枚举阻断 |

## 未实现或仅局部读取：差异保留，暂不修改

| 表/模块 | main 与规范差异 | 本次边界 |
|---|---|---|
| attachment | file_name/size/hash，缺object_key/content_type/uploaded_at；CLEAN对PASSED | 只被工单附件ID列表读到；保留main整表及CLEAN筛选，不补上传/扫描/下载字段 |
| case_candidate | structured_content TEXT；masking=PENDING/MASKED；status=PENDING/PRIORITY/REVIEWED；cluster_id扩展 | 尚无案例治理服务，原字段和枚举不动；不映射成PENDING_MASKING等规范状态 |
| knowledge_cluster | similarity_basis VARCHAR200；status=PENDING/MERGED/SUSPECTED；无updated_at | 尚无聚类治理，整表保持；不改成JSON/OPEN/MERGED/DISMISSED |
| category_field_def | field_id/name/options/sort_order，对规范field_definition/field_key/options_json/definition_version | 动态字段管理未实现，保留原表，不新增第二份定义事实 |
| ticket_field_value | 自增id、字符串定义快照/值，对规范复合键与JSON值 | 未实现动态字段值服务，整表保持 |
| ticket_message | 无sender_type/client_message_id/sent_at等 | 独立工单聊天未实现，整表保持；咨询消息对齐不连带扩展它 |
| engineer_status_log | 自增ID/状态来源日志，规范清单无此表 | 不删除历史日志结构；在线运行状态使用已实现engineer_runtime_state |
| work_calendar | 旧逐日工作时间，含TIME秒精度 | 原结构保留用于历史核对；运行服务已改规范日历 |

## 兼容扩展与范围内的事实边界

- `user_account.password_hash`：main已实现本地 BCrypt 登录的过渡字段，不是规范身份事实；只保留现有哈希，没有添加明文口令。
- `ticket.category_snapshot/asset_check_status/impact_scope/urgency_level/auto_accepted/reopen_count/idempotency_key/first_response_at/solved_at/rating_score/rating_comment/rated_at`：维持main已实现UI/处理/SLA行为，规范性质、状态、快照、主版本仍用canonical列。
- 草稿保留 `title/description/impact_description/urgency_description/location/contact/asset_id` 作为现有接口投影，`creator_id/payload_json` 是共享草稿契约。地点/联系方式255。
- `sla_instance.priority_snapshot/near_breach_notified`：保留优先级快照和80%提醒去重的实现，不另建一份SLA事实。
- `notification.title/content/action_url` 是现有通知展示扩展；`read_at` 已在SQL-010定义。`exception_queue.title/detail/priority` 是已实现列表展示扩展，resolution统一映射reason。
- `knowledge_version.search_text` 与ngram全文索引是由content_json重建的搜索投影，没有扩展未实现知识审核服务。
- 规范SQL-010路由唯一键包含effective_at；本次以可执行SQL定义为准，没有使用DM摘要中省略生效时刻的旧描述建第二个冲突约束。

## 验证与升级证据

初始化只执行一份同名表DDL和统一seed，不再出现 `USE it_consultation` 或针对原配置/知识表的TRUNCATE。升级位于 `db/migration`，不会混入空库init。V2_0显式复制到staging并校验，V2_1原子换名保留20张被替换原表；其余8表完全不动。旧三库只提供显式导入边界与核对流程，不自动导入、不静默覆盖。

静态门禁验证34表范围、规范字段/类型/索引、未实现表逐字不变和单库初始化；MySQL验证使用新建本机隔离实例与唯一`schema_test_*`库，检查真实建表、seed、RAG全文索引、main样本迁移、原表保留、UTC转换和失败门禁。详细操作、可重跑测试与存量SLA/日历阻断边界见 `it-ticket-cloud/db/README.md`；测试通过不代表实际业务数据库已经执行迁移。

2026-09-29 实测：MySQL **8.0.43** 独立本机实例，静态契约测试 **7/7** 通过，真实SQL验证 **7组** 通过（包括34表空库、样本升级、暂缓模块旧值保留、缺时区阻断、未知枚举阻断、旧SLA依据缺失阻断、staging后行数漂移阻断）。元数据门禁在空库与升级后的库都返回零差异。所有测试均使用新建临时库，未连接原开发实例或远程业务库。

同日补充实际接口联调：三个应用以独立本机端口启动、关闭服务注册发现、连接同一临时库并禁用外部模型。7 组路径通过：规范用户登录/姓名、知识管理员平台权限拒绝、分类查询、咨询分配与工程师首次回复、新旧草稿互通、建单幂等及异步咨询转单回调/SLA/通知查询、结束咨询后禁止发消息。接口测试会等待提交后的异步回调完成，不要求回调先于建单响应；测试应用与临时 MySQL 已停止，原服务未重启。
