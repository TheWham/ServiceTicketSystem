package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 知识库版本实体 (KnowledgeVersion) - 对应数据库表 `knowledge_version`
 * ============================================================================
 *
 * 【契约规范说明 (DM-004 / PRD §16.3-16.4)】：
 * 1. 版本不可变性：知识发布后按版本快照留痕，修改产生新版本（version_no 递增），历史不可篡改。
 * 2. 映射 MySQL 物理字段：version_id, article_id, version_no, title, content, author_id, reviewer_id,
 *    recheck_by, change_note, reject_reason, published_at, created_at。
 * 3. reviewer_id 记录审核人（用于"作者不得自审"守卫）；recheck_by 记录高风险知识的平台管理员复核人。
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

    /** 知识文档标题 (100 字符内，对应 MySQL title 字段) */
    private String title;

    /** 知识正文快照内容 (对应 MySQL content 字段) */
    private String content;

    /** 创建/编写人 User ID */
    private String authorId;

    /** 审核人 User ID (未审核为空) */
    private String reviewerId;

    /** 高风险知识的平台管理员复核人（PRD §16.4：账号权限/安全/数据恢复等须增加复核） */
    private String recheckBy;

    /** 版本变更说明/修订日志 */
    private String changeNote;

    /** 驳回原因（SM-KNOWLEDGE-001：PENDING_REVIEW ➔ DRAFT 必须有驳回原因） */
    private String rejectReason;

    /** 正式发布生效时间戳 */
    private LocalDateTime publishedAt;

    /** 创建时间 */
    private LocalDateTime createdAt;

    /** 扩展属性/结构化正文快照 (非数据库物理字段，避免 SQL 语法异常) */
    @TableField(exist = false)
    private String contentJson;
}
