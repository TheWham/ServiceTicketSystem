-- ============================================================
-- consultation-service 库结构(it_consultation)
-- 契约来源:DM-004 / SQL-010(docs/specs/06-mysql-ddl-and-migrations.md)
-- 范围:智能客服(AI 咨询)与转人工。字段、类型、索引与唯一键逐条对齐 SQL-010,
--       不引入 SQL-010 未定义的业务列。
--
-- 表分两类:
--   [OWNED]  本服务事实源,只有本服务可写。
--   [LOCAL]  一期本地承载的配置/知识只读投影。SQL-010 把它们归在平台域/知识域,
--            待 admin-service、knowledge-service 落地后迁出,本服务改为只读适配器。
-- 时间列语义:应用统一按 UTC 写入 DATETIME(6)(DM-001.1),连接不做时区换算。
-- ============================================================

USE it_consultation;

-- ---------- [OWNED] 咨询与消息 ----------
CREATE TABLE consultation (
  session_id          VARCHAR(32)  NOT NULL COMMENT '会话ID,CS 前缀(DM-003)',
  creator_id          VARCHAR(64)  NOT NULL COMMENT '发起员工',
  category_id         VARCHAR(64)  DEFAULT NULL COMMENT '咨询分类,转人工前可为空',
  status              VARCHAR(32)  NOT NULL COMMENT 'ConsultationStatus',
  current_engineer_id VARCHAR(64)  DEFAULT NULL COMMENT '当前责任工程师',
  source              VARCHAR(32)  NOT NULL COMMENT 'ConsultationSource',
  resolution_type     VARCHAR(32)  DEFAULT NULL COMMENT 'ConsultationResolutionType',
  converted_ticket_id VARCHAR(32)  DEFAULT NULL COMMENT '转出的工单ID',
  closed_at           DATETIME(6)  DEFAULT NULL,
  version             BIGINT       NOT NULL DEFAULT 0 COMMENT '乐观锁(DM-001)',
  created_at          DATETIME(6)  NOT NULL,
  updated_at          DATETIME(6)  NOT NULL,
  PRIMARY KEY (session_id),
  KEY idx_consult_creator (creator_id, status, created_at),
  KEY idx_consult_engineer (current_engineer_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='咨询会话[OWNED]';

CREATE TABLE consultation_message (
  message_id        VARCHAR(64)   NOT NULL,
  session_id        VARCHAR(32)   NOT NULL,
  sender_id         VARCHAR(64)   DEFAULT NULL COMMENT 'AI/SYSTEM 发送时为空',
  sender_type       VARCHAR(32)   NOT NULL COMMENT 'MessageSenderType',
  client_message_id VARCHAR(64)   NOT NULL COMMENT '客户端消息ID,重发防重(RD-002)',
  content           MEDIUMTEXT    NOT NULL,
  citation_json     JSON          DEFAULT NULL COMMENT 'AI 回答的 KnowledgeCitation 列表',
  sent_at           DATETIME(6)   NOT NULL,
  withdrawn_at      DATETIME(6)   DEFAULT NULL,
  withdraw_reason   VARCHAR(2000) DEFAULT NULL,
  created_at        DATETIME(6)   NOT NULL,
  updated_at        DATETIME(6)   NOT NULL,
  PRIMARY KEY (message_id),
  KEY idx_consult_message (session_id, sent_at, message_id),
  UNIQUE KEY uk_consult_client_message (session_id, client_message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='咨询消息,只追加[OWNED]';

-- ---------- [OWNED] AI 审计 ----------
CREATE TABLE ai_interaction (
  interaction_id          VARCHAR(64)  NOT NULL,
  session_id              VARCHAR(32)  NOT NULL,
  model_version           VARCHAR(128) NOT NULL,
  retrieved_versions_json JSON         NOT NULL COMMENT '命中的 knowledge_version.version_id 列表',
  confidence              DECIMAL(8,4) DEFAULT NULL,
  feedback                VARCHAR(32)  DEFAULT NULL COMMENT 'AiFeedbackType',
  latency_ms              BIGINT       NOT NULL,
  occurred_at             DATETIME(6)  NOT NULL,
  created_at              DATETIME(6)  NOT NULL,
  updated_at              DATETIME(6)  NOT NULL,
  PRIMARY KEY (interaction_id),
  KEY idx_ai_session (session_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 回答审计元数据,不存提示词与推理过程(AI-008)[OWNED]';

-- ---------- [OWNED] 分配与 SLA ----------
CREATE TABLE assignment (
  assignment_id     VARCHAR(64)  NOT NULL,
  biz_type          VARCHAR(32)  NOT NULL COMMENT 'AssignmentBizType,本服务恒为 CONSULTATION',
  biz_id            VARCHAR(64)  NOT NULL,
  engineer_id       VARCHAR(64)  NOT NULL,
  assigned_at       DATETIME(6)  NOT NULL,
  response_deadline DATETIME(6)  DEFAULT NULL,
  responded_at      DATETIME(6)  DEFAULT NULL,
  end_reason        VARCHAR(32)  DEFAULT NULL COMMENT 'AssignmentEndReason,NULL 表示进行中',
  created_at        DATETIME(6)  NOT NULL,
  updated_at        DATETIME(6)  NOT NULL,
  PRIMARY KEY (assignment_id),
  KEY idx_assignment_object (biz_type, biz_id, assigned_at),
  KEY idx_assignment_engineer (engineer_id, end_reason)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人工分配任务[OWNED]';

CREATE TABLE sla_instance (
  sla_id               VARCHAR(64) NOT NULL,
  biz_type             VARCHAR(32) NOT NULL,
  biz_id               VARCHAR(64) NOT NULL,
  sla_type             VARCHAR(32) NOT NULL COMMENT 'SlaType,本服务恒为 CONSULTATION_RESPONSE',
  status               VARCHAR(32) NOT NULL COMMENT 'SlaStatus',
  target_work_seconds  BIGINT      NOT NULL,
  elapsed_work_seconds BIGINT      NOT NULL DEFAULT 0,
  paused_seconds       BIGINT      NOT NULL DEFAULT 0,
  target_at            DATETIME(6) DEFAULT NULL,
  breached_at          DATETIME(6) DEFAULT NULL,
  met_at               DATETIME(6) DEFAULT NULL,
  calendar_id          VARCHAR(64) NOT NULL,
  calendar_version     BIGINT      NOT NULL,
  version              BIGINT      NOT NULL DEFAULT 0,
  created_at           DATETIME(6) NOT NULL,
  updated_at           DATETIME(6) NOT NULL,
  PRIMARY KEY (sla_id),
  UNIQUE KEY uk_sla_business (biz_type, biz_id, sla_type),
  KEY idx_sla_due (status, target_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='SLA 投影[OWNED]';

-- ---------- [OWNED] 运行时基础设施 ----------
CREATE TABLE idempotency_record (
  record_id       VARCHAR(64)  NOT NULL,
  owner_id        VARCHAR(64)  NOT NULL,
  operation       VARCHAR(128) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  request_hash    CHAR(64)     NOT NULL,
  status          VARCHAR(32)  NOT NULL COMMENT 'IdempotencyStatus',
  result_json     JSON         DEFAULT NULL,
  expires_at      DATETIME(6)  NOT NULL,
  created_at      DATETIME(6)  NOT NULL,
  updated_at      DATETIME(6)  NOT NULL,
  PRIMARY KEY (record_id),
  UNIQUE KEY uk_idempotency (owner_id, operation, idempotency_key),
  KEY idx_idempotency_expiry (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='幂等记录(RD-002)[OWNED]';

CREATE TABLE outbox_event (
  event_id          VARCHAR(64) NOT NULL,
  event_type        VARCHAR(64) NOT NULL,
  aggregate_type    VARCHAR(64) NOT NULL,
  aggregate_id      VARCHAR(64) NOT NULL,
  event_version     INT         NOT NULL,
  aggregate_version BIGINT      NOT NULL,
  payload_json      JSON        NOT NULL COMMENT 'EV-001 envelope',
  status            VARCHAR(32) NOT NULL COMMENT 'OutboxStatus',
  attempts          INT         NOT NULL DEFAULT 0,
  next_attempt_at   DATETIME(6) DEFAULT NULL,
  published_at      DATETIME(6) DEFAULT NULL,
  created_at        DATETIME(6) NOT NULL,
  updated_at        DATETIME(6) NOT NULL,
  PRIMARY KEY (event_id),
  KEY idx_outbox_publish (status, next_attempt_at),
  UNIQUE KEY uk_aggregate_version (aggregate_type, aggregate_id, aggregate_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='领域事件 Outbox(EV-002)[OWNED]';

CREATE TABLE audit_log (
  audit_id    VARCHAR(64)   NOT NULL,
  actor_id    VARCHAR(64)   DEFAULT NULL,
  action      VARCHAR(128)  NOT NULL,
  object_type VARCHAR(64)   NOT NULL,
  object_id   VARCHAR(64)   NOT NULL,
  before_json JSON          DEFAULT NULL,
  after_json  JSON          DEFAULT NULL,
  reason      VARCHAR(2000) DEFAULT NULL,
  request_id  VARCHAR(128)  NOT NULL,
  occurred_at DATETIME(6)   NOT NULL,
  created_at  DATETIME(6)   NOT NULL,
  updated_at  DATETIME(6)   NOT NULL,
  PRIMARY KEY (audit_id),
  KEY idx_audit_object (object_type, object_id, occurred_at),
  KEY idx_audit_actor (actor_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审计,只追加[OWNED]';

CREATE TABLE exception_queue (
  exception_id VARCHAR(64) NOT NULL,
  object_type  VARCHAR(32) NOT NULL,
  object_id    VARCHAR(64) NOT NULL,
  reason_code  VARCHAR(64) NOT NULL,
  status       VARCHAR(32) NOT NULL,
  claimed_by   VARCHAR(64) DEFAULT NULL,
  claimed_at   DATETIME(6) DEFAULT NULL,
  resolved_by  VARCHAR(64) DEFAULT NULL,
  resolved_at  DATETIME(6) DEFAULT NULL,
  reason       TEXT,
  created_at   DATETIME(6) NOT NULL,
  updated_at   DATETIME(6) NOT NULL,
  PRIMARY KEY (exception_id),
  KEY idx_exception_status (status, created_at),
  UNIQUE KEY uk_exception_open (object_type, object_id, reason_code, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异常队列(RD-005)[OWNED]';

-- ---------- [LOCAL] 分类路由与工程师状态 ----------
CREATE TABLE category (
  category_id        VARCHAR(64)  NOT NULL,
  parent_id          VARCHAR(64)  DEFAULT NULL,
  nature             VARCHAR(32)  NOT NULL,
  name               VARCHAR(255) NOT NULL,
  level              SMALLINT     NOT NULL,
  definition_version VARCHAR(64)  NOT NULL,
  enabled            TINYINT(1)   NOT NULL,
  version            BIGINT       NOT NULL DEFAULT 0,
  created_at         DATETIME(6)  NOT NULL,
  updated_at         DATETIME(6)  NOT NULL,
  PRIMARY KEY (category_id),
  KEY idx_category_parent (parent_id, level, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分类[LOCAL]';

CREATE TABLE support_team (
  team_id    VARCHAR(64)  NOT NULL,
  name       VARCHAR(255) NOT NULL,
  enabled    TINYINT(1)   NOT NULL,
  version    BIGINT       NOT NULL DEFAULT 0,
  created_at DATETIME(6)  NOT NULL,
  updated_at DATETIME(6)  NOT NULL,
  PRIMARY KEY (team_id),
  UNIQUE KEY uk_team_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支持团队[LOCAL]';

CREATE TABLE team_member (
  team_id     VARCHAR(64) NOT NULL,
  engineer_id VARCHAR(64) NOT NULL,
  joined_at   DATETIME(6) NOT NULL,
  left_at     DATETIME(6) DEFAULT NULL,
  enabled     TINYINT(1)  NOT NULL,
  created_at  DATETIME(6) NOT NULL,
  updated_at  DATETIME(6) NOT NULL,
  PRIMARY KEY (team_id, engineer_id),
  KEY idx_member_engineer (engineer_id, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='团队成员[LOCAL]';

CREATE TABLE category_route (
  category_id  VARCHAR(64) NOT NULL,
  team_id      VARCHAR(64) NOT NULL,
  route_order  INT         NOT NULL,
  effective_at DATETIME(6) NOT NULL,
  expired_at   DATETIME(6) DEFAULT NULL,
  created_at   DATETIME(6) NOT NULL,
  updated_at   DATETIME(6) NOT NULL,
  PRIMARY KEY (category_id, team_id, effective_at),
  UNIQUE KEY uk_route_order (category_id, route_order, effective_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分类到团队的有序路由[LOCAL]';

CREATE TABLE engineer_runtime_state (
  engineer_id      VARCHAR(64) NOT NULL,
  presence         VARCHAR(32) NOT NULL COMMENT 'EngineerPresence',
  last_activity_at DATETIME(6) DEFAULT NULL,
  last_assigned_at DATETIME(6) DEFAULT NULL,
  version          BIGINT      NOT NULL DEFAULT 0,
  created_at       DATETIME(6) NOT NULL,
  updated_at       DATETIME(6) NOT NULL,
  PRIMARY KEY (engineer_id),
  KEY idx_engineer_presence (presence, last_activity_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工程师在线状态[LOCAL]';

CREATE TABLE engineer_category_capability (
  engineer_id  VARCHAR(64) NOT NULL,
  category_id  VARCHAR(64) NOT NULL,
  team_id      VARCHAR(64) NOT NULL,
  enabled      TINYINT(1)  NOT NULL,
  effective_at DATETIME(6) NOT NULL,
  expired_at   DATETIME(6) DEFAULT NULL,
  created_at   DATETIME(6) NOT NULL,
  updated_at   DATETIME(6) NOT NULL,
  PRIMARY KEY (engineer_id, category_id, team_id, effective_at),
  KEY idx_capability_route (category_id, team_id, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工程师可接分类[LOCAL]';

-- ---------- [LOCAL] 服务日历 ----------
CREATE TABLE service_calendar (
  calendar_id         VARCHAR(64) NOT NULL,
  timezone            VARCHAR(64) NOT NULL,
  work_week_json      JSON        NOT NULL COMMENT 'ISO 工作日数组,如 [1,2,3,4,5]',
  work_intervals_json JSON        NOT NULL COMMENT '工作时段数组',
  lunch_pauses        TINYINT(1)  NOT NULL DEFAULT 1,
  version             BIGINT      NOT NULL DEFAULT 0,
  effective_from      DATETIME(6) NOT NULL,
  effective_to        DATETIME(6) DEFAULT NULL,
  created_at          DATETIME(6) NOT NULL,
  updated_at          DATETIME(6) NOT NULL,
  PRIMARY KEY (calendar_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='服务日历[LOCAL]';

CREATE TABLE calendar_holiday (
  holiday_id     VARCHAR(64)  NOT NULL,
  calendar_id    VARCHAR(64)  NOT NULL,
  holiday_date   DATE         NOT NULL,
  name           VARCHAR(255) NOT NULL,
  is_working_day TINYINT(1)   NOT NULL DEFAULT 0,
  PRIMARY KEY (holiday_id),
  UNIQUE KEY uk_calendar_date (calendar_id, holiday_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='节假日与调休[LOCAL]';

-- ---------- [LOCAL] 知识只读投影(RAG 与知识搜索的来源) ----------
CREATE TABLE knowledge_article (
  article_id         VARCHAR(64) NOT NULL,
  status             VARCHAR(32) NOT NULL COMMENT 'KnowledgeStatus',
  current_version_id VARCHAR(64) DEFAULT NULL,
  category_id        VARCHAR(64) NOT NULL,
  risk_level         VARCHAR(32) NOT NULL COMMENT 'KnowledgeRiskLevel',
  version            BIGINT      NOT NULL DEFAULT 0,
  created_at         DATETIME(6) NOT NULL,
  updated_at         DATETIME(6) NOT NULL,
  PRIMARY KEY (article_id),
  KEY idx_knowledge_status (status, category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识文章[LOCAL]';

-- content_json 结构:{'title':'...','summary':'...','body':'...','keywords':'...'}
-- 检索列 search_text 是 content_json 的生成列,用于 ngram 全文索引;
-- 生成列不是新业务字段,只是可重建的检索投影(DM-001 允许的查询投影)。
CREATE TABLE knowledge_version (
  version_id   VARCHAR(64)   NOT NULL,
  article_id   VARCHAR(64)   NOT NULL,
  version_no   INT           NOT NULL,
  content_json JSON          NOT NULL,
  search_text  TEXT GENERATED ALWAYS AS (
                 CONCAT_WS(' ',
                   JSON_UNQUOTE(JSON_EXTRACT(content_json, '$.title')),
                   JSON_UNQUOTE(JSON_EXTRACT(content_json, '$.summary')),
                   JSON_UNQUOTE(JSON_EXTRACT(content_json, '$.keywords')),
                   JSON_UNQUOTE(JSON_EXTRACT(content_json, '$.body')))) STORED,
  author_id    VARCHAR(64)   NOT NULL,
  reviewer_id  VARCHAR(64)   DEFAULT NULL,
  published_at DATETIME(6)   DEFAULT NULL,
  change_note  VARCHAR(2000) DEFAULT NULL,
  platform_reviewer_id     VARCHAR(64) DEFAULT NULL COMMENT '高风险知识的平台管理员复核人(SM-KNOWLEDGE-001)',
  platform_reviewed_at     DATETIME(6) DEFAULT NULL,
  platform_review_decision VARCHAR(32) DEFAULT NULL,
  created_at   DATETIME(6)   NOT NULL,
  updated_at   DATETIME(6)   NOT NULL,
  PRIMARY KEY (version_id),
  UNIQUE KEY uk_knowledge_version (article_id, version_no),
  FULLTEXT KEY ft_knowledge_search (search_text) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识版本[LOCAL]';
