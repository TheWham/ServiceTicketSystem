package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.enums.KnowledgeStatus;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 知识库文章实体 (KnowledgeArticle) - 对应数据库表 `knowledge_article`
 * ============================================================================
 *
 * 【契约规范说明】（路径相对仓库根目录 docs/）：
 * 1. 业务主键：不可变字符串业务 ID（如 "art-1718000000000"）。
 * 2. 状态生命周期：DRAFT ➔ PENDING_REVIEW ➔ PUBLISHED ➔ OFFLINE
 *    （PRD §16.3 · IT服务工单系统PRD-Ultimate.md:504；
 *    SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90）。
 * 3. 映射 MySQL 物理字段：article_id, category_id, status, current_version_id, risk_level, version, created_at, updated_at
 *    （DM-004 核心持久化实体 · specs/01-data-model-strong-types.md:100）。
 * 4. 已发布知识不得物理删除，只允许下线、发布新版本或回滚
 *    （PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515）。
 * 5. version 列为物理乐观锁（SQL-010 · specs/06-mysql-ddl-and-migrations.md:202），
 *    每次状态迁移递增并作为 Outbox 事件的 aggregate_version（EV-008 · specs/07-domain-events-outbox-redis.md:85）。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@TableName("knowledge_article")
public class KnowledgeArticle {
    /** 知识文章业务主键 ID */
    @TableId(value = "article_id", type = IdType.INPUT)
    private String articleId;

    /** 列表展示的当前版本标题，不写入文章表。 */
    @TableField(exist = false)
    private String title;

    /** 知识所属业务分类 ID (如 C_NET, C_SW, C_HW 等) */
    private String categoryId;

    /** 文章当前发布/流转状态（四态契约见 enums/KnowledgeStatus） */
    private KnowledgeStatus status;

    /** 当前生效/发布的版本 ID (关联 knowledge_version.version_id) */
    private String currentVersionId;

    /** 知识风险等级 (NORMAL-常规, HIGH-高风险运维) */
    private KnowledgeRiskLevel riskLevel;

    /** 创建时间 */
    private LocalDateTime createdAt;

    /** 更新时间 */
    private LocalDateTime updatedAt;

    /**
     * 乐观锁版本号：每次状态迁移递增，WHERE 条件携带旧值以保证并发安全
     * （SM-001 · specs/03-business-state-machine.md:12；SQL-010 · specs/06-mysql-ddl-and-migrations.md:202）。
     * 同时作为 Outbox 事件的 aggregate_version（EV-008 · specs/07-domain-events-outbox-redis.md:85）。
     */
    @Version
    private Long version;
}
