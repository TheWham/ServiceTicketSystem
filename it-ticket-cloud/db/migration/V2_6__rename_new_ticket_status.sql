-- ============================================================================
-- V2_6__rename_new_ticket_status.sql
-- ----------------------------------------------------------------------------
-- 删除历史 NEW 状态，统一为 PENDING_ASSIGNMENT（待分配）。
--
-- 语义：NEW 原本表示“已提交，系统正在路由/尚未分配工程师”，与“待分配”完全一致。
-- 本次为单向迁移：先放开旧检查约束，转换既有业务行，再用新枚举收紧约束。
-- 不保留 NEW 别名或兼容分支；应用代码只识别 PENDING_ASSIGNMENT。
-- ============================================================================

ALTER TABLE ticket
    DROP CHECK ck_ticket_status;

UPDATE ticket
SET status = 'PENDING_ASSIGNMENT'
WHERE status = 'NEW';

ALTER TABLE ticket
    ADD CONSTRAINT ck_ticket_status CHECK (
        status IN ('PENDING_ASSIGNMENT','ASSIGNED','IN_PROGRESS','PENDING_SUPPLEMENT',
                   'PENDING_EXTERNAL','PENDING_ACCEPTANCE','COMPLETED','CANCELLED','CLOSED')
    );

ALTER TABLE ticket_transition
    DROP CHECK ck_ticket_transition_from_status,
    DROP CHECK ck_ticket_transition_to_status;

UPDATE ticket_transition
SET from_status = 'PENDING_ASSIGNMENT'
WHERE from_status = 'NEW';

UPDATE ticket_transition
SET to_status = 'PENDING_ASSIGNMENT'
WHERE to_status = 'NEW';

ALTER TABLE ticket_transition
    ADD CONSTRAINT ck_ticket_transition_from_status CHECK (
        from_status IN ('PENDING_ASSIGNMENT','ASSIGNED','IN_PROGRESS','PENDING_SUPPLEMENT',
                        'PENDING_EXTERNAL','PENDING_ACCEPTANCE','COMPLETED','CANCELLED','CLOSED')
    ),
    ADD CONSTRAINT ck_ticket_transition_to_status CHECK (
        to_status IN ('PENDING_ASSIGNMENT','ASSIGNED','IN_PROGRESS','PENDING_SUPPLEMENT',
                      'PENDING_EXTERNAL','PENDING_ACCEPTANCE','COMPLETED','CANCELLED','CLOSED')
    );
