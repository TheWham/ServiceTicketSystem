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
 * 【契约规范说明 (DM-003 / DM 契约)】：
 * 1. 版本不可变性：知识发布后按版本快照留痕，修改产生新版本（version_no 递增），历史不可篡改。
 * 2. 结构化正文快照：content_json 存储包含标题、切片数、原始正文与发布元数据的 JSON 结构。
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

    /** 结构化正文快照 (JSON 格式，包含标题、切片数与正文内容) */
    private String contentJson;

    /** 创建/编写人 User ID */
    private String authorId;

    /** 审核人 User ID (未审核为空) */
    private String reviewerId;

    /** 正式发布生效时间戳 */
    private LocalDateTime publishedAt;

    /** 版本变更说明/修订日志 */
    private String changeNote;
}
