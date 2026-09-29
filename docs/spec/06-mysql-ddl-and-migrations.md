# MySQL DDL 与迁移契约

| 项目 | 约束 |
|---|---|
| 规范编号 | SQL |
| 事实源 | MySQL 8.x；事务由 Spring `@Transactional` 管理 |
| 数据访问 | MyBatis/MyBatis-Plus；禁止 ORM 自动建表 |
| 字段权威 | `DM-001`、`DM-002`、`DM-004` |
| 状态/副作用 | `SM-*`、`RD-*`；本文件不重复实体字段和状态矩阵 |

## SQL-001 迁移工具与顺序

生产迁移必须使用 Flyway 或等价的版本化 SQL runner。每个脚本只前进一个版本、可审计；回滚采用补偿脚本，不在生产执行破坏性 down migration。脚本路径约定为 `db/migration/V<major>_<minor>__<description>.sql`，应用启动不得隐式建表。

1. `V1_0` 建立字符集、迁移锁和迁移审计表，连接时区固定 UTC。
2. `V1_1` 建立身份、组织、角色、团队和分类/路由/字段定义表。
3. `V1_2` 建立咨询、消息、工单、草稿、补充、外部等待、解决、验收、附件表。
4. `V1_3` 建立分配、SLA、服务日历、异常队列、通知、审计、幂等和 Outbox 表。
5. `V1_4` 建立案例、知识、知识版本、聚类和 AI 交互表。
6. `V1_5` 执行旧数据转换、校验、切换读流量并保留兼容窗口。

脚本需先在影子库和备份恢复副本执行。大表索引使用在线 DDL；迁移记录发布版本、执行人、起止时间和校验结果。

## SQL-002 DDL 基线

每张 DM 实体表必须使用 InnoDB、utf8mb4、UTC `DATETIME(6)`、显式主键、`created_at/updated_at`；可变业务对象含 `version BIGINT`。枚举是 `VARCHAR`，禁止 MySQL `ENUM`。JSON 只能承载 DM-004 已定义快照或元数据，不藏可查询核心字段。

按 DM-004 建表并落实其主键、唯一键和索引。表组清单作为迁移验收锚点：

| 表组 | 表名 | 验收重点 |
|---|---|---|
| 身份 | `user_account`, `user_role`, `support_team`, `team_member` | 员工号唯一、禁用账号不可登录、角色撤销可追溯 |
| 配置 | `category`, `category_route`, `field_definition` | 末级路由唯一、定义版本可快照 |
| 咨询 | `consultation`, `consultation_message` | 状态/责任人投影和消息追加写 |
| 工单 | `ticket`, `ticket_transition`, `ticket_message`, `ticket_draft`, `supplement_request`, `external_wait`, `ticket_resolution`, `ticket_acceptance`, `attachment` | 状态与历史分离；私密正文不可物理删除 |
| 运行 | `assignment`, `sla_instance`, `sla_pause`, `service_calendar`, `calendar_holiday`, `exception_queue`, `notification`, `audit_log`, `idempotency_record`, `outbox_event` | 唯一幂等键、SLA 可重算、异常可人工处理 |
| 知识/AI | `case_candidate`, `knowledge_article`, `knowledge_version`, `knowledge_cluster`, `ai_interaction` | 仅一个当前发布版本、索引版本可追溯 |

`service_calendar`、`calendar_holiday`、`exception_queue` 是对 DM-004 运行投影的实现补充，字段和状态需按本契约的职责实现；不把它们作为状态机事实的替代。

## SQL-003 旧结构映射边界

当前旧脚本只含 `ticket`、`ticket_flow_log`、`notification_log`，并使用中文 ENUM、合并式附件 URL 和 `client_token`。迁移必须先复制到 staging 表并生成报告，禁止直接原表改名上线。

| 旧结构 | 新结构 | 转换规则 |
|---|---|---|
| `ticket.ticket_id` | `ticket.ticket_id` | 保留合法 ID；不合法值建立映射表并记录原值 |
| 基础文本/人员/资产/时间 | 同名 DM 字段 | 按 DM 长度校验，超长不截断，进入异常 |
| 中文分类 | `category_id` | 用冻结字典映射；无法唯一映射需父代理/用户定夺 |
| 中文优先级 | `priority` | 固定字典转换，未知值拒绝迁移 |
| 中文状态 | `ticket.status` | `待处理→NEW`、`处理中→IN_PROGRESS`、`待补充→PENDING_SUPPLEMENT`、`待外部→PENDING_EXTERNAL`、`待验收→PENDING_ACCEPTANCE`、`已完成→COMPLETED`、`已取消→CANCELLED`；其它值需定夺 |
| `client_token` | `idempotency_record` | 仅 owner、operation、请求摘要可确定时迁移 |
| `attachment_urls` | `attachment` | 无法证明安全扫描状态的附件设 ERROR，不标记可下载 |
| `first_response_at` | `assignment.responded_at` | 无责任人时进入迁移异常报告 |
| `solved_at`/评价 | 解决和验收历史 | 无法判断自动验收或员工验收时需定夺 |
| `ticket_flow_log` | `ticket_transition` | `remark→reason`；无事件码时使用不可复用的 legacy 标识 |
| `notification_log` | `notification` | 旧企微/短信到一期渠道的映射需父代理/用户定夺 |

## SQL-004 双写与切换

迁移期间旧写接口进入只读窗口，先全量复制，再以 CDC 或应用双写追平。新模型为唯一读源，旧表仅回滚参考；双写失败进入迁移 Outbox。切换前必须完成行数对账、主键/唯一键校验、状态覆盖、附件安全状态、审计链和权限抽样查询。

## SQL-005 MyBatis 约束

Mapper SQL 显式列名、显式 `version` 条件和受控更新字段。状态更新必须带 `WHERE id AND version`，影响行数为 0 返回并发冲突。批量历史写入不得绕过审计/Outbox 事务；Redis 不参与数据库提交判定。配置、字段定义、路由和服务日历变更必须保存版本快照，历史工单只能读取提交时快照。

## SQL-006 上线验收

- 新库可从零执行全部版本脚本并通过 DM-004 索引检查。
- 旧库样本迁移可重复运行且不产生重复业务对象。
- 任一未知枚举、孤立引用或无法判断的通道/状态阻止切换并输出报告。
- 主业务、历史、幂等、审计和 Outbox 在 DM-005 事务边界内一致。
- 恢复后按 RD-011 校验状态、审计、附件、SLA、异常队列和事件。


## SQL-007 可执行基线 DDL

以下片段是 V1_2/V1_3 的最小可执行基线；DM-004 仍是 Java 字段权威，任何增加列必须同时更新 DM 和迁移版本。

~~~sql
CREATE TABLE ticket (
  ticket_id VARCHAR(32) PRIMARY KEY, creator_id VARCHAR(64) NOT NULL,
  ticket_nature VARCHAR(32) NOT NULL, category_id VARCHAR(64) NOT NULL,
  title VARCHAR(100) NOT NULL, description TEXT NOT NULL,
  impact_description TEXT NOT NULL, urgency_description TEXT NOT NULL,
  location VARCHAR(255), contact VARCHAR(255), asset_id VARCHAR(64),
  status VARCHAR(32) NOT NULL, priority VARCHAR(32) NOT NULL,
  assignee_id VARCHAR(64), source_session_id VARCHAR(32),
  field_snapshot_json JSON, version BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  completed_at DATETIME(6), closed_at DATETIME(6),
  KEY idx_ticket_creator_status (creator_id,status),
  KEY idx_ticket_assignee_status (assignee_id,status),
  KEY idx_ticket_priority_status (priority,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket_field_value (
  ticket_id VARCHAR(32) NOT NULL, field_definition_id VARCHAR(64) NOT NULL,
  field_key VARCHAR(128) NOT NULL, value_json JSON NOT NULL,
  definition_version VARCHAR(64) NOT NULL, created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (ticket_id,field_definition_id),
  KEY idx_field_lookup (field_definition_id,field_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket_transition (
  transition_id VARCHAR(64) PRIMARY KEY, ticket_id VARCHAR(32) NOT NULL,
  from_status VARCHAR(32), to_status VARCHAR(32) NOT NULL,
  event_code VARCHAR(64) NOT NULL, operator_id VARCHAR(64) NOT NULL,
  reason TEXT, occurred_at DATETIME(6) NOT NULL,
  UNIQUE KEY uk_transition_order (ticket_id,occurred_at,transition_id),
  KEY idx_transition_ticket (ticket_id,occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket_duplicate (
  relation_id VARCHAR(64) PRIMARY KEY, source_ticket_id VARCHAR(32) NOT NULL,
  master_ticket_id VARCHAR(32) NOT NULL, reason VARCHAR(2000) NOT NULL,
  created_by VARCHAR(64) NOT NULL, created_at DATETIME(6) NOT NULL,
  UNIQUE KEY uk_duplicate_source (source_ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE attachment_access (
  access_id VARCHAR(64) PRIMARY KEY, attachment_id VARCHAR(64) NOT NULL,
  subject_id VARCHAR(64) NOT NULL, request_id VARCHAR(128) NOT NULL,
  expires_at DATETIME(6) NOT NULL, accessed_at DATETIME(6),
  access_result VARCHAR(32), revoked_at DATETIME(6), issued_at DATETIME(6) NOT NULL,
  KEY idx_attachment_access (attachment_id,subject_id,expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE service_calendar (
  calendar_id VARCHAR(64) PRIMARY KEY, timezone VARCHAR(64) NOT NULL,
  work_week_json JSON NOT NULL, work_intervals_json JSON NOT NULL,
  lunch_pauses TINYINT(1) NOT NULL DEFAULT 1, version BIGINT NOT NULL DEFAULT 0,
  effective_from DATETIME(6) NOT NULL, effective_to DATETIME(6),
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE calendar_holiday (
  holiday_id VARCHAR(64) PRIMARY KEY, calendar_id VARCHAR(64) NOT NULL,
  holiday_date DATE NOT NULL, name VARCHAR(255) NOT NULL,
  is_working_day TINYINT(1) NOT NULL DEFAULT 0,
  UNIQUE KEY uk_calendar_date (calendar_id,holiday_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE exception_queue (
  exception_id VARCHAR(64) PRIMARY KEY, object_type VARCHAR(32) NOT NULL,
  object_id VARCHAR(64) NOT NULL, reason_code VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL, claimed_by VARCHAR(64), claimed_at DATETIME(6),
  resolved_by VARCHAR(64), resolved_at DATETIME(6), reason TEXT,
  created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
  KEY idx_exception_status (status,created_at),
  UNIQUE KEY uk_exception_open (object_type,object_id,reason_code,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE outbox_delivery (
  delivery_id VARCHAR(64) PRIMARY KEY, event_id VARCHAR(64) NOT NULL,
  stream_name VARCHAR(128) NOT NULL, consumer_group VARCHAR(128) NOT NULL,
  entry_id VARCHAR(128), status VARCHAR(32) NOT NULL,
  attempts INT NOT NULL DEFAULT 0, last_error VARCHAR(1000),
  next_attempt_at DATETIME(6), acked_at DATETIME(6),
  UNIQUE KEY uk_delivery_event_group (event_id,consumer_group),
  KEY idx_delivery_retry (status,next_attempt_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
~~~

outbox_event.status=PUBLISHED 表示已成功写入 Stream；消费者失败只更新 outbox_delivery.status=FAILED/DEAD_LETTER，不把已发布 Outbox 改写为 DEAD_LETTER。ticket_duplicate、ticket_field_value、attachment_access 和 delivery 表必须在 V1_3/V1_4 完成后才能开放对应 API。

## SQL-008 旧表迁移 ALTER

~~~sql
ALTER TABLE ticket RENAME TO ticket_legacy;
-- 随后执行 SQL-007 的显式 CREATE TABLE ticket；不得使用 LIKE 复制旧约束。
CREATE TABLE migration_id_map (
  entity_type VARCHAR(32) NOT NULL, legacy_id VARCHAR(128) NOT NULL,
  new_id VARCHAR(128) NOT NULL, mapping_reason VARCHAR(1000) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY(entity_type,legacy_id), UNIQUE KEY uk_mapping_new(entity_type,new_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
~~~

生产脚本不得直接执行示例 INSERT，必须由经过审计的 staging 转换程序生成显式列名单、错误报告和重放批次。

## SQL-009 完整表清单的版本门禁

空库发布脚本必须为下列每张事实表提供显式 `CREATE TABLE`，缺任一表则 Flyway 校验失败：

`user_account,user_role,support_team,team_member,engineer_runtime_state,engineer_category_capability,category,category_route,field_definition,consultation,consultation_message,ticket,ticket_field_value,ticket_transition,ticket_message,ticket_draft,supplement_request,external_wait,ticket_resolution,ticket_acceptance,attachment,assignment,sla_instance,sla_pause,service_calendar,calendar_holiday,exception_queue,notification,audit_log,idempotency_record,outbox_event,outbox_delivery,ticket_duplicate,attachment_access,case_candidate,knowledge_article,knowledge_version,knowledge_cluster,ai_interaction`。

其中 `ticket_field_value`、`ticket_duplicate`、`attachment_access`、`service_calendar`、`calendar_holiday`、`exception_queue`、`outbox_delivery` 是本规范定义的持久化辅助实体；其列定义以 SQL-007 为权威，不能在 MyBatis Entity 中自行增删。其余表的列定义以 DM-004 为权威，迁移生成器逐字段展开 Java/MySQL 映射，不允许 `CREATE TABLE ... LIKE`、ORM auto-DDL 或未声明列。

版本门禁 SQL 查询 `information_schema.tables/statistics/columns`，验证上述表、DM-004 索引、`ticket_id VARCHAR(32)`、枚举 `VARCHAR`、时间 `DATETIME(6)`、版本列和唯一键；校验结果作为迁移制品归档。SQL-007 是新增辅助实体与核心 ticket 的规范 DDL，不代表其余表可省略。



## SQL-010 空库全量 DDL（按执行顺序）

本节与 SQL-007 合并构成 V1 空库脚本：先执行本节 identity/config/consultation 组，再执行 SQL-007 的 ticket 与辅助表，再执行本节 runtime/knowledge 组。MySQL 8.x 使用 CHECK 约束；部署采用逻辑外键，跨表引用由事务服务校验，避免迁移锁放大。

~~~sql
CREATE TABLE user_account (
 user_id VARCHAR(64) PRIMARY KEY, employee_no VARCHAR(64) NOT NULL,
 display_name VARCHAR(255) NOT NULL, department_id VARCHAR(64) NOT NULL,
 identity_source VARCHAR(64) NOT NULL, enabled TINYINT(1) NOT NULL,
 last_identity_sync_at DATETIME(6), version BIGINT NOT NULL DEFAULT 0,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 UNIQUE KEY uk_user_employee_no(employee_no), KEY idx_user_department(department_id),
 KEY idx_user_enabled(enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_role (
 user_id VARCHAR(64) NOT NULL, role_code VARCHAR(32) NOT NULL,
 granted_by VARCHAR(64) NOT NULL, granted_at DATETIME(6) NOT NULL,
 revoked_at DATETIME(6), created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 PRIMARY KEY(user_id,role_code), KEY idx_role_revoked(revoked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE support_team (
 team_id VARCHAR(64) PRIMARY KEY, name VARCHAR(255) NOT NULL, enabled TINYINT(1) NOT NULL,
 version BIGINT NOT NULL DEFAULT 0, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, UNIQUE KEY uk_team_name(name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE team_member (
 team_id VARCHAR(64) NOT NULL, engineer_id VARCHAR(64) NOT NULL,
 joined_at DATETIME(6) NOT NULL, left_at DATETIME(6), enabled TINYINT(1) NOT NULL,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 PRIMARY KEY(team_id,engineer_id), KEY idx_member_engineer(engineer_id,enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE engineer_runtime_state (
 engineer_id VARCHAR(64) PRIMARY KEY, presence VARCHAR(32) NOT NULL,
 last_activity_at DATETIME(6), last_assigned_at DATETIME(6),
 version BIGINT NOT NULL DEFAULT 0, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, KEY idx_engineer_presence(presence,last_activity_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE engineer_category_capability (
 engineer_id VARCHAR(64) NOT NULL, category_id VARCHAR(64) NOT NULL,
 team_id VARCHAR(64) NOT NULL, enabled TINYINT(1) NOT NULL,
 effective_at DATETIME(6) NOT NULL, expired_at DATETIME(6),
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 PRIMARY KEY(engineer_id,category_id,team_id,effective_at),
 KEY idx_capability_route(category_id,team_id,enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE category (
 category_id VARCHAR(64) PRIMARY KEY, parent_id VARCHAR(64),
 nature VARCHAR(32) NOT NULL, name VARCHAR(255) NOT NULL, level SMALLINT NOT NULL,
 definition_version VARCHAR(64) NOT NULL, enabled TINYINT(1) NOT NULL,
 version BIGINT NOT NULL DEFAULT 0, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, KEY idx_category_parent(parent_id,level,enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE category_route (
 category_id VARCHAR(64) NOT NULL, team_id VARCHAR(64) NOT NULL,
 route_order INT NOT NULL, effective_at DATETIME(6) NOT NULL, expired_at DATETIME(6),
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 PRIMARY KEY(category_id,team_id,effective_at),
 UNIQUE KEY uk_route_order(category_id,route_order,effective_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE field_definition (
 field_definition_id VARCHAR(64) PRIMARY KEY, category_id VARCHAR(64) NOT NULL,
 field_key VARCHAR(128) NOT NULL, field_type VARCHAR(32) NOT NULL,
 required TINYINT(1) NOT NULL, options_json JSON, display_order INT NOT NULL,
 enabled TINYINT(1) NOT NULL, definition_version VARCHAR(64) NOT NULL,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 UNIQUE KEY uk_field_version(category_id,field_key,definition_version),
 KEY idx_field_category(category_id,enabled,display_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE consultation (
 session_id VARCHAR(32) PRIMARY KEY, creator_id VARCHAR(64) NOT NULL,
 category_id VARCHAR(64), status VARCHAR(32) NOT NULL, current_engineer_id VARCHAR(64),
 source VARCHAR(32) NOT NULL, resolution_type VARCHAR(32), converted_ticket_id VARCHAR(32),
 closed_at DATETIME(6), version BIGINT NOT NULL DEFAULT 0,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 KEY idx_consult_creator(creator_id,status,created_at),
 KEY idx_consult_engineer(current_engineer_id,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE consultation_message (
 message_id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(32) NOT NULL,
 sender_id VARCHAR(64), sender_type VARCHAR(32) NOT NULL, client_message_id VARCHAR(64) NOT NULL,
 content MEDIUMTEXT NOT NULL,
 citation_json JSON, sent_at DATETIME(6) NOT NULL, withdrawn_at DATETIME(6),
 withdraw_reason VARCHAR(2000), created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL,
 KEY idx_consult_message(session_id,sent_at,message_id),
 UNIQUE KEY uk_consult_client_message(session_id,client_message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket_message (
 message_id VARCHAR(64) PRIMARY KEY, ticket_id VARCHAR(32) NOT NULL,
 sender_id VARCHAR(64), sender_type VARCHAR(32) NOT NULL, client_message_id VARCHAR(64) NOT NULL,
 content MEDIUMTEXT NOT NULL,
 sent_at DATETIME(6) NOT NULL, withdrawn_at DATETIME(6), withdraw_reason VARCHAR(2000),
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 KEY idx_ticket_message(ticket_id,sent_at,message_id),
 UNIQUE KEY uk_ticket_client_message(ticket_id,client_message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket_draft (
 draft_id VARCHAR(64) PRIMARY KEY, creator_id VARCHAR(64) NOT NULL,
 nature VARCHAR(32), category_id VARCHAR(64), payload_json JSON NOT NULL,
 last_saved_at DATETIME(6) NOT NULL, expires_at DATETIME(6) NOT NULL,
 version BIGINT NOT NULL DEFAULT 0, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, UNIQUE KEY uk_active_draft(creator_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE supplement_request (
 request_id VARCHAR(64) PRIMARY KEY, ticket_id VARCHAR(32) NOT NULL,
 sequence_no INT NOT NULL, requested_by VARCHAR(64) NOT NULL, content TEXT NOT NULL,
 requested_at DATETIME(6) NOT NULL, responded_at DATETIME(6),
 overdue_closed TINYINT(1) NOT NULL DEFAULT 0, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, UNIQUE KEY uk_supplement_seq(ticket_id,sequence_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE external_wait (
 wait_id VARCHAR(64) PRIMARY KEY, ticket_id VARCHAR(32) NOT NULL,
 dependency_type VARCHAR(32) NOT NULL, reason VARCHAR(2000) NOT NULL,
 expected_at DATETIME(6) NOT NULL, started_at DATETIME(6) NOT NULL,
 ended_at DATETIME(6), resume_note VARCHAR(2000),
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 KEY idx_external_wait(ticket_id,started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket_resolution (
 resolution_id VARCHAR(64) PRIMARY KEY, ticket_id VARCHAR(32) NOT NULL,
 solution MEDIUMTEXT NOT NULL, verification TEXT NOT NULL, submitted_by VARCHAR(64) NOT NULL,
 submitted_at DATETIME(6) NOT NULL, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, KEY idx_resolution(ticket_id,submitted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket_acceptance (
 acceptance_id VARCHAR(64) PRIMARY KEY, ticket_id VARCHAR(32) NOT NULL,
 result VARCHAR(32) NOT NULL, reason VARCHAR(2000), operator_id VARCHAR(64),
 occurred_at DATETIME(6) NOT NULL, rating_score TINYINT,
 rating_comment VARCHAR(2000), rated_at DATETIME(6), created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, KEY idx_acceptance(ticket_id,occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE attachment (
 attachment_id VARCHAR(64) PRIMARY KEY, biz_type VARCHAR(32) NOT NULL,
 biz_id VARCHAR(64) NOT NULL, uploader_id VARCHAR(64) NOT NULL,
 object_key VARCHAR(512) NOT NULL, original_name VARCHAR(255) NOT NULL,
 size_bytes BIGINT NOT NULL, sha256 CHAR(64) NOT NULL, content_type VARCHAR(255) NOT NULL,
 scan_status VARCHAR(32) NOT NULL, uploaded_at DATETIME(6) NOT NULL,
 withdrawn_at DATETIME(6), created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 UNIQUE KEY uk_attachment_hash(biz_type,biz_id,sha256), UNIQUE KEY uk_object_key(object_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE assignment (
 assignment_id VARCHAR(64) PRIMARY KEY, biz_type VARCHAR(32) NOT NULL,
 biz_id VARCHAR(64) NOT NULL, engineer_id VARCHAR(64) NOT NULL,
 assigned_at DATETIME(6) NOT NULL, response_deadline DATETIME(6),
 responded_at DATETIME(6), end_reason VARCHAR(32),
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 KEY idx_assignment_object(biz_type,biz_id,assigned_at),
 KEY idx_assignment_engineer(engineer_id,end_reason)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sla_instance (
 sla_id VARCHAR(64) PRIMARY KEY, biz_type VARCHAR(32) NOT NULL,
 biz_id VARCHAR(64) NOT NULL, sla_type VARCHAR(32) NOT NULL, status VARCHAR(32) NOT NULL,
 target_work_seconds BIGINT NOT NULL, elapsed_work_seconds BIGINT NOT NULL DEFAULT 0,
 paused_seconds BIGINT NOT NULL DEFAULT 0, target_at DATETIME(6),
 breached_at DATETIME(6), met_at DATETIME(6), calendar_id VARCHAR(64) NOT NULL,
 calendar_version BIGINT NOT NULL, version BIGINT NOT NULL DEFAULT 0,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 UNIQUE KEY uk_sla_business(biz_type,biz_id,sla_type),
 KEY idx_sla_due(status,target_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sla_pause (
 pause_id VARCHAR(64) PRIMARY KEY, sla_id VARCHAR(64) NOT NULL,
 reason_type VARCHAR(32) NOT NULL, started_at DATETIME(6) NOT NULL,
 ended_at DATETIME(6), operator_id VARCHAR(64) NOT NULL,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 KEY idx_sla_pause(sla_id,started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE notification (
 notification_id VARCHAR(64) PRIMARY KEY, event_id VARCHAR(64) NOT NULL,
 receiver_id VARCHAR(64) NOT NULL, channel VARCHAR(32) NOT NULL,
 dedup_key VARCHAR(255) NOT NULL, status VARCHAR(32) NOT NULL,
 attempts INT NOT NULL DEFAULT 0, last_error VARCHAR(1000), sent_at DATETIME(6),
 read_at DATETIME(6), created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 UNIQUE KEY uk_notification_dedup(dedup_key), KEY idx_notification_receiver(receiver_id,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE audit_log (
 audit_id VARCHAR(64) PRIMARY KEY, actor_id VARCHAR(64), action VARCHAR(128) NOT NULL,
 object_type VARCHAR(64) NOT NULL, object_id VARCHAR(64) NOT NULL,
 before_json JSON, after_json JSON, reason VARCHAR(2000), request_id VARCHAR(128) NOT NULL,
 occurred_at DATETIME(6) NOT NULL, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL,
 KEY idx_audit_object(object_type,object_id,occurred_at),
 KEY idx_audit_actor(actor_id,occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE idempotency_record (
 record_id VARCHAR(64) PRIMARY KEY, owner_id VARCHAR(64) NOT NULL,
 operation VARCHAR(128) NOT NULL, idempotency_key VARCHAR(128) NOT NULL,
 request_hash CHAR(64) NOT NULL, status VARCHAR(32) NOT NULL, result_json JSON,
 expires_at DATETIME(6) NOT NULL, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL,
 UNIQUE KEY uk_idempotency(owner_id,operation,idempotency_key),
 KEY idx_idempotency_expiry(expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE outbox_event (
 event_id VARCHAR(64) PRIMARY KEY, event_type VARCHAR(64) NOT NULL,
 aggregate_type VARCHAR(64) NOT NULL, aggregate_id VARCHAR(64) NOT NULL,
 event_version INT NOT NULL, aggregate_version BIGINT NOT NULL,
 payload_json JSON NOT NULL, status VARCHAR(32) NOT NULL,
 attempts INT NOT NULL DEFAULT 0, next_attempt_at DATETIME(6),
 published_at DATETIME(6), created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL,
 KEY idx_outbox_publish(status,next_attempt_at),
 UNIQUE KEY uk_aggregate_version(aggregate_type,aggregate_id,aggregate_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE case_candidate (
 case_id VARCHAR(64) PRIMARY KEY, source_type VARCHAR(32) NOT NULL,
 source_id VARCHAR(64) NOT NULL, structured_content_json JSON NOT NULL,
 masking_status VARCHAR(32) NOT NULL, reusable_flag TINYINT(1) NOT NULL,
 status VARCHAR(32) NOT NULL, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, UNIQUE KEY uk_case_source(source_type,source_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE knowledge_article (
 article_id VARCHAR(64) PRIMARY KEY, status VARCHAR(32) NOT NULL,
 current_version_id VARCHAR(64), category_id VARCHAR(64) NOT NULL,
 risk_level VARCHAR(32) NOT NULL, version BIGINT NOT NULL DEFAULT 0,
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 KEY idx_knowledge_status(status,category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE knowledge_version (
 version_id VARCHAR(64) PRIMARY KEY, article_id VARCHAR(64) NOT NULL,
 version_no INT NOT NULL, content_json JSON NOT NULL, author_id VARCHAR(64) NOT NULL,
 reviewer_id VARCHAR(64), published_at DATETIME(6), change_note VARCHAR(2000),
 platform_reviewer_id VARCHAR(64), platform_reviewed_at DATETIME(6),
 platform_review_decision VARCHAR(32),
 created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL,
 UNIQUE KEY uk_knowledge_version(article_id,version_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE knowledge_cluster (
 cluster_id VARCHAR(64) PRIMARY KEY, similarity_basis JSON NOT NULL,
 status VARCHAR(32) NOT NULL, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, KEY idx_cluster_status(status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ai_interaction (
 interaction_id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(32) NOT NULL,
 model_version VARCHAR(128) NOT NULL, retrieved_versions_json JSON NOT NULL,
 confidence DECIMAL(8,4), feedback VARCHAR(32), latency_ms BIGINT NOT NULL,
 occurred_at DATETIME(6) NOT NULL, created_at DATETIME(6) NOT NULL,
 updated_at DATETIME(6) NOT NULL, KEY idx_ai_session(session_id,occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
~~~

V1 执行顺序固定为：identity/config → consultation → SQL-007 ticket/auxiliary → runtime → knowledge/AI。任一步失败由 Flyway 终止版本，不继续后续脚本。
