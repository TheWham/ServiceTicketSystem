-- ============================================================
-- IT 服务工单系统 PRD v2.0 建库脚本
-- 依据：PRD v2.0 §20 核心数据实体（23 表）+ §8/§9/§16 状态枚举 + §10.2 固定字段
-- 约定：utf8mb4 / InnoDB；枚举存字符串；业务主键 VARCHAR；全表带 created_at/updated_at
-- 幂等：可重复执行（DROP IF EXISTS + CREATE）
-- ============================================================

CREATE DATABASE IF NOT EXISTS it_ticket_system
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE it_ticket_system;

-- ---------- 身份与组织（§6） ----------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  user_id         VARCHAR(32)  NOT NULL COMMENT '用户标识',
  employee_no     VARCHAR(32)  NOT NULL COMMENT '工号（身份源同步）',
  name            VARCHAR(64)  NOT NULL,
  department_id   VARCHAR(32)  NULL COMMENT '部门（HR 同步）',
  status          VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE' COMMENT 'ACTIVE/DISABLED',
  identity_source VARCHAR(32)  NOT NULL DEFAULT 'SSO',
  created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uk_employee_no (employee_no)
) ENGINE=InnoDB COMMENT='用户（员工不能在本系统改身份信息 §6.1）';

DROP TABLE IF EXISTS user_role;
CREATE TABLE user_role (
  id          BIGINT       NOT NULL AUTO_INCREMENT,
  user_id     VARCHAR(32)  NOT NULL,
  role_code   VARCHAR(32)  NOT NULL COMMENT 'EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KB_ADMIN（§5.1 四角色）',
  granted_by  VARCHAR(32)  NULL,
  granted_at  DATETIME     NOT NULL,
  revoked_at  DATETIME     NULL COMMENT 'NULL=有效',
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_user_role (user_id, role_code)
) ENGINE=InnoDB COMMENT='角色授权（权限包独立授予，一人可多角色）';

DROP TABLE IF EXISTS support_team;
CREATE TABLE support_team (
  team_id    VARCHAR(32) NOT NULL,
  name       VARCHAR(64) NOT NULL,
  status     VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (team_id)
) ENGINE=InnoDB COMMENT='团队';

DROP TABLE IF EXISTS team_member;
CREATE TABLE team_member (
  id          BIGINT      NOT NULL AUTO_INCREMENT,
  team_id     VARCHAR(32) NOT NULL,
  engineer_id VARCHAR(32) NOT NULL,
  joined_at   DATETIME    NOT NULL,
  status      VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_engineer (engineer_id),
  KEY idx_team (team_id)
) ENGINE=InnoDB COMMENT='团队成员';

-- 工程师状态（§6.2）变更历史
DROP TABLE IF EXISTS engineer_status_log;
CREATE TABLE engineer_status_log (
  id           BIGINT      NOT NULL AUTO_INCREMENT,
  engineer_id  VARCHAR(32) NOT NULL,
  status       VARCHAR(16) NOT NULL COMMENT 'AVAILABLE/BUSY/AWAY/OFFLINE',
  source       VARCHAR(16) NOT NULL COMMENT 'MANUAL/AUTO',
  created_at   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_engineer_time (engineer_id, created_at)
) ENGINE=InnoDB COMMENT='工程师状态变更（须保留时间和来源 §6.2）';

-- ---------- 分类与路由（§10.1 / §12.1） ----------
DROP TABLE IF EXISTS category;
CREATE TABLE category (
  category_id   VARCHAR(32)  NOT NULL,
  parent_id     VARCHAR(32)  NULL,
  ticket_nature VARCHAR(20)  NOT NULL COMMENT 'INCIDENT/SERVICE_REQUEST',
  name          VARCHAR(64)  NOT NULL,
  level         TINYINT      NOT NULL COMMENT '1~3，仅末级可提单',
  status        VARCHAR(16)  NOT NULL DEFAULT 'ACTIVE',
  version       INT          NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (category_id),
  KEY idx_parent (parent_id)
) ENGINE=InnoDB COMMENT='分类（最多三级，停用保留快照）';

DROP TABLE IF EXISTS category_route;
CREATE TABLE category_route (
  id           BIGINT      NOT NULL AUTO_INCREMENT,
  category_id  VARCHAR(32) NOT NULL,
  team_id      VARCHAR(32) NOT NULL,
  route_order  INT         NOT NULL COMMENT '有序候选团队',
  effective_at DATETIME    NOT NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_category_order (category_id, route_order)
) ENGINE=InnoDB COMMENT='分类路由（§12.1 分配算法第 1 步）';

-- 分类扩展字段定义（§10.3）
DROP TABLE IF EXISTS category_field_def;
CREATE TABLE category_field_def (
  field_id    VARCHAR(32) NOT NULL,
  category_id VARCHAR(32) NOT NULL,
  name        VARCHAR(64) NOT NULL,
  field_type  VARCHAR(16) NOT NULL COMMENT 'TEXT/RADIO/CHECKBOX/DATE/ATTACHMENT',
  required    TINYINT     NOT NULL DEFAULT 0,
  options     VARCHAR(1000) NULL COMMENT '单选/多选值域 JSON',
  sort_order  INT         NOT NULL DEFAULT 0,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (field_id),
  KEY idx_category (category_id)
) ENGINE=InnoDB COMMENT='分类扩展字段（每末级分类最多 10 个）';

-- ---------- 咨询会话（§8） ----------
DROP TABLE IF EXISTS consultation;
CREATE TABLE consultation (
  session_id          VARCHAR(32) NOT NULL,
  creator_id          VARCHAR(32) NOT NULL,
  category_id         VARCHAR(32) NULL COMMENT '转人工前员工确认分类',
  status              VARCHAR(24) NOT NULL DEFAULT 'AI_ACTIVE'
    COMMENT 'AI_ACTIVE/WAITING_ENGINEER/HUMAN_ACTIVE/PENDING_CONFIRMATION/RESOLVED/CONVERTED_TO_TICKET/CLOSED',
  current_engineer_id VARCHAR(32) NULL,
  source              VARCHAR(16) NOT NULL DEFAULT 'AI' COMMENT 'AI/DIRECT_HUMAN',
  resolved_type       VARCHAR(16) NULL COMMENT 'CONFIRMED/AUTO',
  auto_resolved       TINYINT     NOT NULL DEFAULT 0,
  ticket_id           VARCHAR(32) NULL COMMENT '转工单后关联',
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id),
  KEY idx_creator (creator_id, created_at),
  KEY idx_engineer (current_engineer_id, status)
) ENGINE=InnoDB COMMENT='咨询会话（与工单独立 §2.2）';

DROP TABLE IF EXISTS consultation_message;
CREATE TABLE consultation_message (
  message_id   VARCHAR(32) NOT NULL,
  session_id   VARCHAR(32) NOT NULL,
  sender_id    VARCHAR(32) NOT NULL,
  sender_type  VARCHAR(16) NOT NULL COMMENT 'EMPLOYEE/ENGINEER/AI',
  content      TEXT        NOT NULL,
  withdrawn_at DATETIME    NULL COMMENT '撤回时间；不物理删除 §13.2',
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (message_id),
  KEY idx_session_time (session_id, created_at)
) ENGINE=InnoDB COMMENT='咨询消息（发送后不得编辑）';

-- ---------- 正式工单（§9 / §10.2） ----------
DROP TABLE IF EXISTS ticket;
CREATE TABLE ticket (
  ticket_id           VARCHAR(32) NOT NULL COMMENT '工单编号',
  creator_id          VARCHAR(32) NOT NULL,
  nature              VARCHAR(20) NOT NULL COMMENT 'INCIDENT/SERVICE_REQUEST',
  category_id         VARCHAR(32) NOT NULL COMMENT '末级分类',
  category_snapshot   VARCHAR(500) NULL COMMENT '分类快照（停用分类保留 §10.1）',
  title               VARCHAR(100) NOT NULL COMMENT '1~100 字符',
  description         VARCHAR(5000) NOT NULL COMMENT '10~5000 字符',
  impact_description  VARCHAR(500) NOT NULL COMMENT '影响情况（接单确认用）',
  urgency_description VARCHAR(500) NOT NULL COMMENT '紧急说明',
  location            VARCHAR(200) NULL,
  contact             VARCHAR(64)  NULL COMMENT '本次联系方式，不反写身份源',
  asset_id            VARCHAR(64)  NULL,
  asset_check_status  VARCHAR(16)  NULL COMMENT 'PENDING/VERIFIED（CMDB 超时降级 §10.2）',
  status              VARCHAR(24)  NOT NULL DEFAULT 'NEW'
    COMMENT 'NEW/ASSIGNED/IN_PROGRESS/PENDING_SUPPLEMENT/PENDING_EXTERNAL/PENDING_ACCEPTANCE/COMPLETED/CANCELLED/CLOSED',
  priority            VARCHAR(8)   NOT NULL DEFAULT 'MEDIUM' COMMENT 'HIGH/MEDIUM/LOW（接单时按矩阵确认 §11.4）',
  impact_scope        VARCHAR(16)  NULL COMMENT '影响范围 SINGLE/DEPARTMENT/CROSS_DEPT（接单确认 §11.4）',
  urgency_level       VARCHAR(8)   NULL COMMENT '紧急程度 LOW/MEDIUM/HIGH（接单确认 §11.4）',
  assignee_id         VARCHAR(32)  NULL,
  source_session_id   VARCHAR(32)  NULL COMMENT '咨询转单来源',
  auto_accepted       TINYINT      NOT NULL DEFAULT 0 COMMENT '48h 自动验收标记',
  reopen_count        INT          NOT NULL DEFAULT 0,
  idempotency_key     VARCHAR(64)  NULL COMMENT '提单幂等键（§10.4）',
  version             INT          NOT NULL DEFAULT 0 COMMENT '乐观锁',
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (ticket_id),
  KEY idx_creator (creator_id, created_at),
  KEY idx_assignee_status (assignee_id, status),
  KEY idx_source_session (source_session_id),
  KEY idx_idem (creator_id, idempotency_key)
) ENGINE=InnoDB COMMENT='正式工单主表';

DROP TABLE IF EXISTS ticket_field_value;
CREATE TABLE ticket_field_value (
  id                        BIGINT NOT NULL AUTO_INCREMENT,
  ticket_id                 VARCHAR(32) NOT NULL,
  field_definition_snapshot VARCHAR(1000) NOT NULL COMMENT '提交时字段定义快照 §10.3',
  field_value               VARCHAR(2000) NULL,
  created_at                DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_ticket (ticket_id)
) ENGINE=InnoDB COMMENT='工单扩展字段值（含定义快照）';

DROP TABLE IF EXISTS ticket_transition;
CREATE TABLE ticket_transition (
  transition_id VARCHAR(32) NOT NULL,
  ticket_id     VARCHAR(32) NOT NULL,
  from_status   VARCHAR(24) NULL,
  to_status     VARCHAR(24) NOT NULL,
  event         VARCHAR(32) NOT NULL COMMENT 'SUBMIT/ROUTE/ACCEPT/SUPPLEMENT_REQUEST/...（§9.3）',
  operator_id   VARCHAR(32) NOT NULL COMMENT '含 SYSTEM',
  reason        VARCHAR(500) NULL COMMENT '驳回/撤销/异常关闭必填',
  occurred_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (transition_id),
  KEY idx_ticket_time (ticket_id, occurred_at)
) ENGINE=InnoDB COMMENT='工单流转（只追加，不覆盖 §2.2）';

DROP TABLE IF EXISTS ticket_message;
CREATE TABLE ticket_message (
  message_id   VARCHAR(32) NOT NULL,
  ticket_id    VARCHAR(32) NOT NULL,
  sender_id    VARCHAR(32) NOT NULL,
  content      TEXT        NOT NULL,
  withdrawn_at DATETIME    NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (message_id),
  KEY idx_ticket_time (ticket_id, created_at)
) ENGINE=InnoDB COMMENT='工单聊天（当前双方可见 §13.1）';

-- ---------- 附件（§13.3） ----------
DROP TABLE IF EXISTS attachment;
CREATE TABLE attachment (
  attachment_id VARCHAR(32) NOT NULL,
  biz_type      VARCHAR(16) NOT NULL COMMENT 'CONSULTATION/TICKET',
  biz_id        VARCHAR(32) NOT NULL,
  uploader_id   VARCHAR(32) NOT NULL,
  file_name     VARCHAR(255) NOT NULL,
  size          BIGINT      NOT NULL COMMENT '≤20MB',
  hash          VARCHAR(64) NOT NULL COMMENT '文件哈希',
  scan_status   VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/CLEAN/REJECTED',
  withdrawn_at  DATETIME    NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (attachment_id),
  KEY idx_biz (biz_type, biz_id)
) ENGINE=InnoDB COMMENT='附件（先扫描后可用；保存哈希/上传人/扫描结果）';

-- ---------- 分配与 SLA（§11 / §12） ----------
DROP TABLE IF EXISTS assignment;
CREATE TABLE assignment (
  assignment_id     VARCHAR(32) NOT NULL,
  biz_type          VARCHAR(16) NOT NULL COMMENT 'CONSULTATION/TICKET',
  biz_id            VARCHAR(32) NOT NULL,
  engineer_id       VARCHAR(32) NOT NULL,
  assigned_at       DATETIME NOT NULL,
  response_deadline DATETIME NULL COMMENT '响应 SLA 截止（10 工作分钟）',
  responded_at      DATETIME NULL COMMENT '首次有效响应',
  end_reason        VARCHAR(32) NULL COMMENT 'RESPONDED/TIMEOUT_TRANSFER/TRANSFER_APPLY',
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (assignment_id),
  KEY idx_engineer (engineer_id, assigned_at),
  KEY idx_biz (biz_type, biz_id)
) ENGINE=InnoDB COMMENT='分配记录（转派不删历史责任 §12.3）';

DROP TABLE IF EXISTS sla_instance;
CREATE TABLE sla_instance (
  sla_id               VARCHAR(32) NOT NULL,
  ticket_id            VARCHAR(32) NOT NULL,
  sla_type             VARCHAR(16) NOT NULL COMMENT 'RESPONSE/COMPLETION',
  priority_snapshot    VARCHAR(8)  NOT NULL,
  target_seconds       BIGINT      NOT NULL COMMENT '目标工作秒（按优先级）',
  elapsed_work_seconds BIGINT      NOT NULL DEFAULT 0 COMMENT '累计有效工作秒',
  paused_seconds       BIGINT      NOT NULL DEFAULT 0,
  near_breach_notified TINYINT     NOT NULL DEFAULT 0 COMMENT '80% 提醒标记',
  breach_at            DATETIME    NULL COMMENT '违约时间（不可删除 §11.2）',
  status               VARCHAR(16) NOT NULL DEFAULT 'RUNNING' COMMENT 'RUNNING/PAUSED/STOPPED/BREACHED',
  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (sla_id),
  KEY idx_ticket (ticket_id, sla_type),
  KEY idx_status (status)
) ENGINE=InnoDB COMMENT='SLA 实例（完成 SLA 创建起算，验收阶段不消耗）';

DROP TABLE IF EXISTS sla_pause;
CREATE TABLE sla_pause (
  pause_id    VARCHAR(32) NOT NULL,
  sla_id      VARCHAR(32) NOT NULL,
  reason_type VARCHAR(24) NOT NULL COMMENT 'SUPPLEMENT/EXTERNAL',
  started_at  DATETIME NOT NULL,
  ended_at    DATETIME NULL,
  operator_id VARCHAR(32) NOT NULL,
  PRIMARY KEY (pause_id),
  KEY idx_sla (sla_id)
) ENGINE=InnoDB COMMENT='SLA 暂停（补充/外部等待期间暂停 §11.3）';

-- 服务日历（§11.1）
DROP TABLE IF EXISTS work_calendar;
CREATE TABLE work_calendar (
  id          BIGINT NOT NULL AUTO_INCREMENT,
  cal_date    DATE   NOT NULL,
  day_type    VARCHAR(16) NOT NULL COMMENT 'WORKDAY/HOLIDAY',
  start_time  TIME NULL COMMENT '默认 09:00',
  end_time    TIME NULL COMMENT '默认 18:00',
  lunch_pause TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uk_date (cal_date)
) ENGINE=InnoDB COMMENT='服务日历（节假日平台管理员维护）';

-- ---------- 通知（§14） ----------
DROP TABLE IF EXISTS notification;
CREATE TABLE notification (
  notification_id VARCHAR(32) NOT NULL,
  event_id        VARCHAR(64) NOT NULL COMMENT '领域事件实例 ID',
  receiver_id     VARCHAR(32) NOT NULL,
  channel         VARCHAR(16) NOT NULL COMMENT 'INBOX/EMAIL',
  dedup_key       VARCHAR(128) NOT NULL COMMENT 'event_id:receiver:channel（生命周期唯一 §14.3）',
  title           VARCHAR(100) NULL,
  content         VARCHAR(500) NULL,
  action_url      VARCHAR(200) NULL COMMENT '待办行动入口（查看≠行动 §14.2）',
  status          VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/SENT/FAILED',
  attempts        TINYINT     NOT NULL DEFAULT 0 COMMENT '站内重试 3 次；邮件指数退避',
  last_error      VARCHAR(255) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (notification_id),
  UNIQUE KEY uk_dedup (dedup_key),
  KEY idx_receiver (receiver_id, status, created_at)
) ENGINE=InnoDB COMMENT='通知（幂等键唯一；最终失败入管理员异常记录）';

-- ---------- 案例与知识库（§16） ----------
DROP TABLE IF EXISTS case_candidate;
CREATE TABLE case_candidate (
  case_id            VARCHAR(32) NOT NULL,
  source_type        VARCHAR(16) NOT NULL COMMENT 'TICKET/CONSULTATION',
  source_id          VARCHAR(32) NOT NULL,
  structured_content TEXT        NULL COMMENT '现象/范围/根因/步骤/验证/关键词/分类',
  masking_status     VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/MASKED',
  reusable_flag      TINYINT     NOT NULL DEFAULT 0 COMMENT '工程师标记复用价值',
  status             VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/PRIORITY/REVIEWED',
  cluster_id         VARCHAR(32) NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (case_id),
  KEY idx_status (status, reusable_flag)
) ENGINE=InnoDB COMMENT='案例池（COMPLETED 工单自动进入 §16.1）';

DROP TABLE IF EXISTS knowledge_article;
CREATE TABLE knowledge_article (
  article_id         VARCHAR(32) NOT NULL,
  category_id        VARCHAR(32) NULL,
  status             VARCHAR(20) NOT NULL DEFAULT 'DRAFT' COMMENT 'DRAFT/PENDING_REVIEW/PUBLISHED/OFFLINE（§16.3）',
  current_version_id VARCHAR(32) NULL,
  risk_level         VARCHAR(16) NOT NULL DEFAULT 'NORMAL' COMMENT 'NORMAL/HIGH（高风险须平台管理员复核 §16.4）',
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (article_id),
  KEY idx_status (status)
) ENGINE=InnoDB COMMENT='知识（不物理删除，只下线/新版本/回滚）';

DROP TABLE IF EXISTS knowledge_version;
CREATE TABLE knowledge_version (
  version_id   VARCHAR(32) NOT NULL,
  article_id   VARCHAR(32) NOT NULL,
  version_no   INT         NOT NULL,
  title        VARCHAR(100) NOT NULL,
  content      TEXT        NOT NULL,
  author_id    VARCHAR(32) NOT NULL,
  reviewer_id  VARCHAR(32) NULL COMMENT '审核人（不得自审 §16.4）',
  recheck_by   VARCHAR(32) NULL COMMENT '高风险复核人（平台管理员）',
  change_note  VARCHAR(500) NULL,
  published_at DATETIME    NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (version_id),
  KEY idx_article (article_id, version_no)
) ENGINE=InnoDB COMMENT='知识版本（新版本发布前旧版在线 §16.3）';

DROP TABLE IF EXISTS knowledge_cluster;
CREATE TABLE knowledge_cluster (
  cluster_id       VARCHAR(32) NOT NULL,
  similarity_basis VARCHAR(200) NOT NULL COMMENT '类型/适用系统/现象/根因',
  status           VARCHAR(16) NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/MERGED/SUSPECTED',
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (cluster_id)
) ENGINE=InnoDB COMMENT='知识簇（自动归簇不自动发布 §16.5）';

-- ---------- AI（§17） ----------
DROP TABLE IF EXISTS ai_interaction;
CREATE TABLE ai_interaction (
  interaction_id     VARCHAR(32) NOT NULL,
  session_id         VARCHAR(32) NOT NULL,
  model_version      VARCHAR(64) NOT NULL,
  retrieved_versions VARCHAR(500) NULL COMMENT '引用知识版本 JSON',
  answer             TEXT        NULL,
  confidence         DECIMAL(4,3) NULL,
  refused            TINYINT     NOT NULL DEFAULT 0 COMMENT '拒答标记',
  feedback           VARCHAR(16) NULL COMMENT 'HELPFUL/UNHELPFUL/WRONG',
  latency_ms         INT         NULL,
  created_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (interaction_id),
  KEY idx_session (session_id, created_at)
) ENGINE=InnoDB COMMENT='AI 回答记录（保存模型/来源/置信度/反馈 §17.2）';

-- ---------- 审计（§23） ----------
DROP TABLE IF EXISTS audit_log;
CREATE TABLE audit_log (
  audit_id    BIGINT       NOT NULL AUTO_INCREMENT,
  actor_id    VARCHAR(32)  NOT NULL COMMENT '操作人或 SYSTEM',
  action      VARCHAR(64)  NOT NULL,
  object_type VARCHAR(32)  NOT NULL,
  object_id   VARCHAR(64)  NOT NULL,
  before_value TEXT         NULL,
  after_value  TEXT         NULL,
  reason      VARCHAR(500) NULL,
  request_id  VARCHAR(64)  NULL COMMENT '请求追踪标识',
  result      VARCHAR(16)  NOT NULL DEFAULT 'SUCCESS',
  occurred_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (audit_id),
  KEY idx_object (object_type, object_id, occurred_at),
  KEY idx_actor (actor_id, occurred_at)
) ENGINE=InnoDB COMMENT='审计日志（只追加；业务接口不得修改删除 §23）';

-- ---------- 提单草稿（字段对齐新提单 §10.2，每用户一条） ----------
DROP TABLE IF EXISTS ticket_draft;
CREATE TABLE ticket_draft (
  draft_id            BIGINT NOT NULL AUTO_INCREMENT,
  user_id             VARCHAR(32) NOT NULL COMMENT '用户',
  nature              VARCHAR(16) NULL COMMENT 'INCIDENT/REQUEST',
  category_id         VARCHAR(32) NULL COMMENT '末级分类',
  title               VARCHAR(100) NULL,
  description         VARCHAR(2000) NULL,
  impact_description  VARCHAR(500) NULL,
  urgency_description VARCHAR(500) NULL,
  location            VARCHAR(100) NULL,
  contact             VARCHAR(50) NULL,
  asset_id            VARCHAR(64) NULL,
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (draft_id),
  UNIQUE KEY uk_user (user_id)
) ENGINE=InnoDB COMMENT='提单草稿（每用户一条，字段对齐新提单）';

-- ---------- 异常队列（F-08 / §4 术语 / §18.2 管理员工单干预） ----------
DROP TABLE IF EXISTS exception_queue;
CREATE TABLE exception_queue (
  exception_id   VARCHAR(32) NOT NULL COMMENT '异常单号',
  biz_type       VARCHAR(16) NOT NULL COMMENT 'TICKET/CONSULTATION/NOTIFICATION',
  biz_id         VARCHAR(32) NOT NULL COMMENT '关联业务ID（工单/会话/通知）',
  exception_type VARCHAR(32) NOT NULL COMMENT 'NO_RESPONSE/ROUTE_FAILED/LONG_PENDING/NOTIFY_FAILED/LIMIT_EXCEEDED(转派3次/补充3次/外部等待5工作日)',
  title          VARCHAR(100) NULL COMMENT '异常摘要',
  detail         VARCHAR(1000) NULL COMMENT '异常详情/原因',
  priority       VARCHAR(8)  NULL COMMENT '关联工单优先级',
  status         VARCHAR(16) NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN/RESOLVED/DISMISSED',
  resolved_by    VARCHAR(32) NULL COMMENT '处理人（平台管理员）',
  resolved_at    DATETIME    NULL,
  resolution     VARCHAR(500) NULL COMMENT '处理结果说明（干预必须填原因 §18.2）',
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (exception_id),
  KEY idx_status_type (status, exception_type),
  KEY idx_biz (biz_type, biz_id),
  KEY idx_created (created_at)
) ENGINE=InnoDB COMMENT='异常队列（无人响应/路由失败/长期挂起/通知失败/超限 → 平台管理员处理）';

-- ---------- 种子数据（最小可用） ----------
INSERT INTO `user` (user_id, employee_no, name, department_id) VALUES
  ('U_EMP01', 'E1001', '演示员工', 'D001'),
  ('U_ENG01', 'E2001', '演示工程师', 'D002'),
  ('U_ADM01', 'E3001', '平台管理员', 'D003'),
  ('U_KBA01', 'E4001', '知识库管理员', 'D003')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO user_role (user_id, role_code, granted_by, granted_at) VALUES
  ('U_EMP01', 'EMPLOYEE',      'U_ADM01', NOW()),
  ('U_ENG01', 'ENGINEER',      'U_ADM01', NOW()),
  ('U_ADM01', 'PLATFORM_ADMIN','U_ADM01', NOW()),
  ('U_KBA01', 'KB_ADMIN',      'U_ADM01', NOW())
ON DUPLICATE KEY UPDATE granted_at = VALUES(granted_at);

INSERT INTO support_team (team_id, name) VALUES
  ('T_HW', '硬件支持组'), ('T_SW', '软件支持组'), ('T_NET', '网络支持组')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO team_member (team_id, engineer_id, joined_at) VALUES
  ('T_HW', 'U_ENG01', NOW()), ('T_SW', 'U_ENG01', NOW()), ('T_NET', 'U_ENG01', NOW())
ON DUPLICATE KEY UPDATE joined_at = VALUES(joined_at);

-- 分类：两级示例（INCIDENT 硬件/软件/网络/账号权限/其他）
INSERT INTO category (category_id, parent_id, ticket_nature, name, level) VALUES
  ('C_HW',    NULL, 'INCIDENT', '硬件', 1),
  ('C_SW',    NULL, 'INCIDENT', '软件', 1),
  ('C_NET',   NULL, 'INCIDENT', '网络', 1),
  ('C_ACC',   NULL, 'INCIDENT', '账号权限', 1),
  ('C_OTH',   NULL, 'INCIDENT', '其他', 1),
  ('C_HW_PC', 'C_HW', 'INCIDENT', '台式机/笔记本', 2),
  ('C_HW_PR', 'C_HW', 'INCIDENT', '打印机/外设', 2)
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO category_route (category_id, team_id, route_order, effective_at) VALUES
  ('C_HW_PC', 'T_HW', 1, NOW()),
  ('C_HW_PR', 'T_HW', 1, NOW()),
  ('C_SW',    'T_SW', 1, NOW()),
  ('C_NET',   'T_NET', 1, NOW())
ON DUPLICATE KEY UPDATE route_order = VALUES(route_order);
