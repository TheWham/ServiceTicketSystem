-- ============================================================================
-- V2_4：知识域四表补充表/列注释（纯元数据变更）
-- ============================================================================
-- 只执行 ALTER ... COMMENT / MODIFY COLUMN ... COMMENT，不改列类型、不改数据、
-- 不删除任何对象（遵守远端库只增不删约束）。CHECK 约束与索引不受 MODIFY 影响。
-- knowledge_transition 的表注释在 V2_3 已带，此处仅补列注释。
-- ============================================================================

-- ---------------------------------------------------------------- 表注释
ALTER TABLE knowledge_article
    COMMENT = '知识文章主表：状态机四态与当前版本指针（SM-KNOWLEDGE-001）';

ALTER TABLE knowledge_version
    COMMENT = '知识版本快照：不可变，正文存 content JSON 四键（AC-25 作者/审核留痕）';

ALTER TABLE knowledge_cluster
    COMMENT = '相似知识聚类（预留表，AC-26 聚类治理，当前无功能读写）';

-- ---------------------------------------------------------------- knowledge_article
ALTER TABLE knowledge_article
    MODIFY COLUMN article_id        varchar(64)  NOT NULL                COMMENT '知识文章业务主键（不可变业务 ID）',
    MODIFY COLUMN status            varchar(32)  NOT NULL                COMMENT '当前状态：DRAFT/PENDING_REVIEW/PUBLISHED/OFFLINE（SM-KNOWLEDGE-001）',
    MODIFY COLUMN current_version_id varchar(64) DEFAULT NULL            COMMENT '当前生效版本 ID，指向 knowledge_version.version_id',
    MODIFY COLUMN category_id       varchar(64)  NOT NULL                COMMENT '知识分类编码（如 C_NET/C_SW/C_HW）',
    MODIFY COLUMN risk_level        varchar(32)  NOT NULL                COMMENT '风险等级 NORMAL/HIGH；HIGH 发布须平台管理员复核（PRD §16.4）',
    MODIFY COLUMN version           bigint       NOT NULL DEFAULT '0'    COMMENT '乐观锁版本号：每次状态迁移递增；兼作 outbox 事件 aggregate_version（EV-008）',
    MODIFY COLUMN created_at        datetime(6)  NOT NULL                COMMENT '创建时间',
    MODIFY COLUMN updated_at        datetime(6)  NOT NULL                COMMENT '更新时间';

-- ---------------------------------------------------------------- knowledge_version
ALTER TABLE knowledge_version
    MODIFY COLUMN version_id              varchar(64)   NOT NULL         COMMENT '知识版本业务主键',
    MODIFY COLUMN article_id              varchar(64)   NOT NULL         COMMENT '所属文章 ID，指向 knowledge_article.article_id',
    MODIFY COLUMN version_no              int           NOT NULL         COMMENT '递增版本序号（同文章内唯一，uk_knowledge_version）',
    MODIFY COLUMN content                 json          NOT NULL         COMMENT '知识正文 JSON 四键：title/summary/keywords/body',
    MODIFY COLUMN author_id               varchar(64)   NOT NULL         COMMENT '作者 user ID（AC-25：作者不得自审）',
    MODIFY COLUMN reviewer_id             varchar(64)   DEFAULT NULL     COMMENT '审核人 user ID',
    MODIFY COLUMN published_at            datetime(6)   DEFAULT NULL     COMMENT '正式发布生效时间；草稿态为空',
    MODIFY COLUMN change_note             varchar(2000) DEFAULT NULL     COMMENT '版本变更说明',
    MODIFY COLUMN platform_reviewer_id    varchar(64)   DEFAULT NULL     COMMENT '高风险知识的平台管理员复核人（PRD §16.4）',
    MODIFY COLUMN platform_reviewed_at    datetime(6)   DEFAULT NULL     COMMENT '平台管理员复核时间',
    MODIFY COLUMN platform_review_decision varchar(32)  DEFAULT NULL     COMMENT '平台管理员复核结论（如 APPROVED）',
    MODIFY COLUMN created_at              datetime(6)   NOT NULL         COMMENT '创建时间',
    MODIFY COLUMN updated_at              datetime(6)   NOT NULL         COMMENT '更新时间',
    MODIFY COLUMN search_text             text GENERATED ALWAYS AS (concat_ws(_utf8mb4' ',json_unquote(json_extract(`content`,_utf8mb4'$.title')),json_unquote(json_extract(`content`,_utf8mb4'$.summary')),json_unquote(json_extract(`content`,_utf8mb4'$.keywords')),json_unquote(json_extract(`content`,_utf8mb4'$.body')))) STORED COMMENT '检索投影列：由 content 四键拼接的生成列（ngram 全文索引）';

-- ---------------------------------------------------------------- knowledge_transition
ALTER TABLE knowledge_transition
    MODIFY COLUMN transition_id varchar(64)  NOT NULL         COMMENT '流转记录业务主键',
    MODIFY COLUMN article_id    varchar(64)  NOT NULL         COMMENT '知识文章 ID，指向 knowledge_article.article_id',
    MODIFY COLUMN version_id    varchar(64)  DEFAULT NULL     COMMENT '涉及的知识版本 ID',
    MODIFY COLUMN from_status   varchar(32)  NOT NULL         COMMENT '迁移前状态',
    MODIFY COLUMN to_status     varchar(32)  NOT NULL         COMMENT '迁移后状态',
    MODIFY COLUMN event_code    varchar(64)  NOT NULL         COMMENT '业务动作码 DOMAIN_ACTION（如 KNOWLEDGE_PUBLISH），与领域事件类型严格区分',
    MODIFY COLUMN operator_id   varchar(64)  NOT NULL         COMMENT '操作人 user ID',
    MODIFY COLUMN operator_role varchar(32)  DEFAULT NULL     COMMENT '操作人角色（网关透传值，如 KNOWLEDGE_ADMIN）',
    MODIFY COLUMN reason        varchar(255) DEFAULT NULL     COMMENT '原因或备注：驳回/下线必填',
    MODIFY COLUMN occurred_at   datetime(6)  NOT NULL         COMMENT '迁移发生时间';

-- ---------------------------------------------------------------- knowledge_cluster
ALTER TABLE knowledge_cluster
    MODIFY COLUMN cluster_id       varchar(64) NOT NULL       COMMENT '聚类业务主键',
    MODIFY COLUMN similarity_basis json        NOT NULL       COMMENT '相似度依据（类型/适用系统/现象/根因）',
    MODIFY COLUMN status           varchar(32) NOT NULL       COMMENT '聚类状态：OPEN/MERGED/DISMISSED',
    MODIFY COLUMN created_at       datetime(6) NOT NULL       COMMENT '创建时间',
    MODIFY COLUMN updated_at       datetime(6) NOT NULL       COMMENT '更新时间';
