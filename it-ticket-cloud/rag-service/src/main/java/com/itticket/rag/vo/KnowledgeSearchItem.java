package com.itticket.rag.vo;

/**
 * 知识搜索结果项 —— 契约 AI-004.4（camelCase）。
 *
 * <p>只允许返回已发布文章的字段与分页元数据，不暴露来源工单（AI-004.4）。</p>
 */
public record KnowledgeSearchItem(
        String articleId,
        String versionId,
        String title,
        String summary,
        String categoryId) {
}
