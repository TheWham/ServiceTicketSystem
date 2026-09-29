-- ============================================================
-- 20-rag-lifecycle.sql —— 知识库生命周期与 AI 审计的增量 DDL
-- ------------------------------------------------------------
-- 基线：00-schema.sql（远端 it_ticket_system 已与之一致）
-- 原则：只做增量（CREATE TABLE IF NOT EXISTS / ADD COLUMN），
--       不含任何 DROP / TRUNCATE / DELETE。
-- 契约依据：
--   SM-001      每次迁移追加一条等价审计事件，状态不可覆盖历史 → knowledge_transition
--   SM-001      迁移须校验乐观锁版本                            → knowledge_article.version
--   SM-KNOW-001 驳回必须有原因                                  → knowledge_version.reject_reason
--   SM-EVENT-001/EV-008  知识领域事实事件外发                    → outbox_event
-- ============================================================

-- 1) 乐观锁列（SM-001：迁移在事务内校验当前状态与乐观锁版本）
--    幂等写法：列已存在时跳过（执行侧需先判断 information_schema）
ALTER TABLE `knowledge_article`
    ADD COLUMN `version` BIGINT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号（SM-001）';

-- 2) 驳回原因（SM-KNOWLEDGE-001：驳回必须有原因）
ALTER TABLE `knowledge_version`
    ADD COLUMN `reject_reason` VARCHAR(500) DEFAULT NULL COMMENT '驳回原因（PENDING_REVIEW→DRAFT 必填）';

-- 3) 知识状态流转审计
CREATE TABLE IF NOT EXISTS `knowledge_transition` (
  `transition_id`  varchar(32)  NOT NULL COMMENT '流转记录ID',
  `article_id`     varchar(32)  NOT NULL COMMENT '知识ID',
  `version_id`     varchar(32)  DEFAULT NULL COMMENT '涉及版本（可空）',
  `from_status`    varchar(20)  NOT NULL COMMENT '迁移前状态',
  `to_status`      varchar(20)  NOT NULL COMMENT '迁移后状态',
  `event_code`     varchar(32)  NOT NULL COMMENT 'DOMAIN_ACTION 动作码，如 KNOWLEDGE_PUBLISH',
  `operator_id`    varchar(32)  NOT NULL COMMENT '操作人',
  `operator_role`  varchar(32)  DEFAULT NULL COMMENT '操作人角色',
  `reason`         varchar(500) DEFAULT NULL COMMENT '原因/备注（驳回、下线必填）',
  `occurred_at`    datetime     NOT NULL COMMENT '发生时间',
  PRIMARY KEY (`transition_id`),
  KEY `idx_kt_article` (`article_id`,`occurred_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识状态流转审计（SM-001）';

-- 4) 领域事实事件外发表（EV-007 信封 / EV-008 知识事件）
CREATE TABLE IF NOT EXISTS `outbox_event` (
  `event_id`        varchar(32)   NOT NULL COMMENT '事件ID，全局唯一',
  `event_type`      varchar(48)   NOT NULL COMMENT 'SCREAMING_SNAKE_CASE 领域事实事件类型',
  `event_version`   int           NOT NULL DEFAULT 1 COMMENT '信封版本',
  `aggregate_type`  varchar(32)   NOT NULL COMMENT '聚合类型，如 KNOWLEDGE',
  `aggregate_id`    varchar(32)   NOT NULL COMMENT '聚合ID，如 article_id',
  `payload_json`    varchar(1000) NOT NULL COMMENT 'EV-008 最小载荷（禁止空对象）',
  `status`          varchar(16)   NOT NULL DEFAULT 'PENDING' COMMENT 'PENDING/PUBLISHED/FAILED',
  `attempts`        int           NOT NULL DEFAULT 0 COMMENT '投递尝试次数',
  `next_attempt_at` datetime      DEFAULT NULL COMMENT '下次重试时间',
  `published_at`    datetime      DEFAULT NULL COMMENT '投递成功时间',
  `created_at`      datetime      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`event_id`),
  KEY `idx_outbox_status` (`status`,`next_attempt_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='领域事实事件外发表（EV-007/EV-008）';
