package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 知识库版本实体 (KnowledgeVersion) - 对应数据库表 `knowledge_version`
 * ============================================================================
 *
 * 【权威模型（main 最新，对齐 V2_2 之后形态）】：
 * 1. 正文存于 content 列（JSON），键为 title / summary / keywords / body，
 *    读写统一由 {@link com.itticket.rag.support.KnowledgeContent} 处理。
 * 2. 版本不可变性：发布后按版本快照留痕，修改产生新版本（version_no 递增）
 *    （SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90「新版本发布」迁移）。
 * 3. 审核人 reviewer_id（用于"作者不得自审"守卫，
 *    AC-25 · specs/09-prd-spec-test-traceability.md:91）；高风险知识的平台管理员
 *    复核人 platform_reviewer_id（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515）。
 *
 * 【迁移说明】：
 * - 本实体对齐的是 V2_2 迁移执行后的列（content + created_at/updated_at）。
 * - 执行前远端 knowledge_version 仍是 content_json、无 created_at/updated_at，
 *   届时 rag-service 的插入/查询需等 V2_2 在远端落地后才能正常工作。
 *   此前端依赖已在模块 README 中注明。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@TableName("knowledge_version")
public class KnowledgeVersion {
    /** 知识版本唯一业务 ID */
    @TableId(value = "version_id", type = IdType.INPUT)
    private String versionId;

    /** 所属文章业务 ID (外键关联 knowledge_article.article_id) */
    private String articleId;

    /** 递增版本序号 (如 1, 2, 3) */
    private Integer versionNo;

    /** 知识正文 JSON（V2_2 之后的 content 列），键：title / summary / keywords / body */
    private String content;

    /** 创建/编写人 User ID */
    private String authorId;

    /** 审核人 User ID（作者不得自审，AC-25 · specs/09-prd-spec-test-traceability.md:91） */
    private String reviewerId;

    /** 正式发布生效时间戳 */
    private LocalDateTime publishedAt;

    /** 版本变更说明 */
    private String changeNote;

    /** 高风险知识的平台管理员复核人（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515） */
    private String platformReviewerId;

    /** 平台管理员复核时间 */
    private LocalDateTime platformReviewedAt;

    /** 平台管理员复核结论 */
    private String platformReviewDecision;

    /** 创建时间（V2_2 之后存在） */
    private LocalDateTime createdAt;

    /** 更新时间（V2_2 之后存在） */
    private LocalDateTime updatedAt;

    // ---------------------------------------------------------------- 便捷读取（不入库，也不进 JSON）

    /** 正文标题（从 content JSON 提取） */
    @JsonIgnore
    public String getTitle() {
        return com.itticket.rag.support.KnowledgeContent.titleOf(content);
    }

    /** 正文全文（从 content JSON 提取 body） */
    @JsonIgnore
    public String getBody() {
        return com.itticket.rag.support.KnowledgeContent.bodyOf(content);
    }

    /** 摘要（从 content JSON 提取 summary） */
    @JsonIgnore
    public String getSummary() {
        return com.itticket.rag.support.KnowledgeContent.summaryOf(content);
    }

    /** 关键词（从 content JSON 提取 keywords） */
    @JsonIgnore
    public String getKeywords() {
        return com.itticket.rag.support.KnowledgeContent.keywordsOf(content);
    }
}
