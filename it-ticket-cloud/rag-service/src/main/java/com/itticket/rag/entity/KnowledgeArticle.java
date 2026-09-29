package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.enums.KnowledgeStatus;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 知识库文章实体 (KnowledgeArticle) - 对应数据库表 `knowledge_article`
 * ============================================================================
 *
 * 【契约规范说明 (DM-003 / DM 契约)】：
 * 1. 业务主键：不可变字符串业务 ID（如 "art-1718000000000"）。
 * 2. 状态生命周期：DRAFT (草稿) -> SUBMITTED (提交) -> REVIEWED (已审) -> PUBLISHED (已发布) -> ARCHIVED (已归档)。
 * 3. 映射 MySQL 物理字段：article_id, category_id, status, current_version_id, risk_level, created_at, updated_at。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@TableName("knowledge_article")
public class KnowledgeArticle {
    /** 知识文章业务主键 ID */
    @TableId(value = "article_id", type = IdType.INPUT)
    private String articleId;

    /** 知识所属业务分类 ID (如 C_NET, C_SW, C_HW 等) */
    private String categoryId;

    /** 文章当前发布/流转状态 */
    private KnowledgeStatus status;

    /** 当前生效/发布的版本 ID (关联 knowledge_version.version_id) */
    private String currentVersionId;

    /** 知识风险等级 (NORMAL-常规, HIGH-高风险运维) */
    private KnowledgeRiskLevel riskLevel;

    /** 创建时间 */
    private LocalDateTime createdAt;

    /** 更新时间 */
    private LocalDateTime updatedAt;

    /** 乐观锁/逻辑版本标记 (非数据库物理字段，避免 SQL 语法异常) */
    @TableField(exist = false)
    private Long version;
}
