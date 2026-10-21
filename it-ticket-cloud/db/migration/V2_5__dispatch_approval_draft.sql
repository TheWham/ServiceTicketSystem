-- ============================================================================
-- V2_5__dispatch_approval_draft.sql
-- ----------------------------------------------------------------------------
-- 派单草案（HITL 写操作门禁）承载表。
--
-- 需求依据：
--   docs/IT服务工单系统-需求归因文档.md —— 功能 D（F-02 + P1 自动派单）：
--     「强制 Human-in-the-Loop 人机确认（派单草案主管点击才生效）；
--       派单幂等防重与失败补偿」
--   PRD-Ultimate F-06 自动派单 / §12 路由。
--
-- 设计说明：
--   1. 路由不再直接落分派，改为先产出「派单草案」挂起，等待有派单权的
--      审批人确认后才真正写 assignment。审批人角色取 PRD §98 的角色定义
--      （「系统不设置主管和坐台客服角色」），即 PLATFORM_ADMIN。
--   2. 专表而非复用 exception_queue：异常队列承载的是「需要人工介入的故障」，
--      其 uk_exception_open(object_type,object_id,reason_code,status) 把 status 也编进
--      唯一键，因此同一业务同一原因只要可重复结案就会在第二次结案时撞键；
--      派单草案是常规工作流实例，同一工单可先后产生多份（首次派单、超时转派），
--      因此单独建表，且唯一键只约束「待确认」态，不与终态历史冲突。
--   3. 超时语义对齐讲义「专属 Token 含超时失效」：expires_at 到期即失效，
--      扫描器将其置为 EXPIRED（失败补偿记录即为草案行本身），工单保持 NEW 并通知审批人。
--   4. 草稿载荷直接落列（与 ticket_draft 的 payload_json 惯例一致），
--      单份待确认草案由生成列 uk_dispatch_draft_pending 保证。
--
-- 幂等：本迁移为纯增量（CREATE TABLE ... IF NOT EXISTS），不含 DROP / TRUNCATE / DELETE。
--   注意 MySQL 一条 ALTER/CREATE 只能执行一次，重复执行会因索引已存在而报错，
--   与既有 V2_1/V2_2 迁移脚本同等的执行契约（由迁移框架保证只跑一次）。
-- ============================================================================

CREATE TABLE IF NOT EXISTS dispatch_draft (
    draft_id         VARCHAR(64)  PRIMARY KEY,
    ticket_id        VARCHAR(32)  NOT NULL,
    status           VARCHAR(32)  NOT NULL,
    engineer_id      VARCHAR(64)  NOT NULL,
    engineer_name    VARCHAR(255),
    team_id          VARCHAR(64),
    priority         VARCHAR(32),
    category_id      VARCHAR(64),
    selection_note   VARCHAR(500),
    payload_json     JSON         NOT NULL,
    idempotency_key  VARCHAR(128) NOT NULL,
    version          BIGINT       NOT NULL DEFAULT 0,
    expires_at       DATETIME(6)  NOT NULL,
    claimed_by       VARCHAR(64),
    claimed_at       DATETIME(6),
    resolved_by      VARCHAR(64),
    resolved_at      DATETIME(6),
    reason           TEXT,
    created_at       DATETIME(6)  NOT NULL,
    updated_at       DATETIME(6)  NOT NULL,
    pending_ticket_id VARCHAR(32) GENERATED ALWAYS AS (CASE WHEN status='PENDING' THEN ticket_id ELSE NULL END) STORED,
    UNIQUE KEY uk_dispatch_draft_pending (pending_ticket_id),
    UNIQUE KEY uk_dispatch_draft_idem (ticket_id, idempotency_key),
    KEY idx_dispatch_draft_status (status, created_at),
    CONSTRAINT ck_dispatch_draft_status CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;