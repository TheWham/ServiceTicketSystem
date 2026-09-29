package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.KnowledgeRiskLevel;
import com.itticket.consultation.enums.KnowledgeStatus;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 知识文章(DM-004)。[LOCAL] 本服务只读:AI 与知识搜索只允许读取 status=PUBLISHED
 * 且 versionId 等于 currentVersionId 的版本(AI-001、AI-API-005)。
 */
@Data
@TableName("knowledge_article")
public class KnowledgeArticle {

    @TableId(value = "article_id", type = IdType.INPUT)
    private String articleId;
    private KnowledgeStatus status;
    private String currentVersionId;
    private String categoryId;
    private KnowledgeRiskLevel riskLevel;
    private Long version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
