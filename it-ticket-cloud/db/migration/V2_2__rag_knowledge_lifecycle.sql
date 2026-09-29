-- ============================================================================
-- V2_2__rag_knowledge_lifecycle.sql
-- ----------------------------------------------------------------------------
-- 知识状态迁移审计表（rag-service）。
--
-- 契约依据：
--   SM-001       每个合法迁移必须追加一条等价审计记录，实体状态不可覆盖历史；
--   SM-KNOWLEDGE-001  DRAFT → PENDING_REVIEW → PUBLISHED → OFFLINE 及其驳回、下线动作。
--
-- 说明：
--   1. 权威模型中 knowledge_* 三表由 V2_0 / V2_1 建立，但未包含知识域的状态迁移审计表，
--      故本迁移单独补一张（纯增量，不含任何 DROP / TRUNCATE / DELETE）。
--   2. event_code 存 DOMAIN_ACTION 动作码（如 KNOWLEDGE_PUBLISH）；
--      领域事实事件类型（KNOWLEDGE_PUBLISHED 等）写入 outbox_event.event_type，两者不得混用。
--   3. 驳回、下线的原因写入 reason（knowledge_version 不再有 reject_reason 列）。
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_transition (
    transition_id VARCHAR(64) PRIMARY KEY,
    article_id    VARCHAR(64) NOT NULL,
    version_id    VARCHAR(64),
    from_status   VARCHAR(32) NOT NULL,
    to_status     VARCHAR(32) NOT NULL,
    event_code    VARCHAR(64) NOT NULL,
    operator_id   VARCHAR(64) NOT NULL,
    operator_role VARCHAR(32),
    reason        VARCHAR(255),
    occurred_at   DATETIME(6) NOT NULL,
    KEY idx_kt_article (article_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识状态迁移审计（SM-001）';
