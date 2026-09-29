package com.itticket.consultation.dto;

/** AI-003 / AI-004.4。只暴露已发布文章的元数据,不暴露来源工单。 */
public record KnowledgeSearchItem(
        String articleId,
        String versionId,
        String title,
        String summary,
        String categoryId) {
}
