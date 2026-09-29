package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 知识库版本实体 (KnowledgeVersion) - 对应数据库表 `knowledge_version`
 * ============================================================================
 *
 * 【权威模型（与 db/init/00-schema.sql 及远端实际列一致）】：
 * 1. 正文存于 content_json（JSON），键为 title / summary / keywords / body，
 *    读写统一由 {@link com.itticket.rag.support.KnowledgeContent} 处理。
 * 2. 版本不可变性：发布后按版本快照留痕，修改产生新版本（version_no 递增）。
 * 3. 审核人 reviewer_id（用于"作者不得自审"守卫，AC-25）；高风险知识的平台管理员
 *    复核人 platform_reviewer_id（PRD §16.4）。
 *
 * 【与 00-schema.sql 的差异（远端实际列）】：
 * 远端 knowledge_version 暂无 created_at / updated_at 两列，change_note 为 varchar(255)。
 * 此处按远端实际列映射，避免读取 schema 声明时产生不存在的列。
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

    /** 知识正文 JSON，键：title / summary / keywords / body */
    private String contentJson;

    /** 创建/编写人 User ID */
    private String authorId;

    /** 审核人 User ID（作者不得自审，AC-25） */
    private String reviewerId;

    /** 正式发布生效时间戳 */
    private LocalDateTime publishedAt;

    /** 版本变更说明（远端为 varchar(255)） */
    private String changeNote;

    /** 高风险知识的平台管理员复核人（PRD §16.4） */
    private String platformReviewerId;

    /** 平台管理员复核时间 */
    private LocalDateTime platformReviewedAt;

    /** 平台管理员复核结论 */
    private String platformReviewDecision;

    // ---------------------------------------------------------------- 便捷访问（不入库）

    /** 正文标题（从 content_json 提取） */
    public String getTitle() {
        return com.itticket.rag.support.KnowledgeContent.titleOf(contentJson);
    }

    /** 正文全文（从 content_json 提取 body） */
    public String getContent() {
        return com.itticket.rag.support.KnowledgeContent.bodyOf(contentJson);
    }

    /** 摘要（从 content_json 提取 summary） */
    public String getSummary() {
        return com.itticket.rag.support.KnowledgeContent.summaryOf(contentJson);
    }
}
