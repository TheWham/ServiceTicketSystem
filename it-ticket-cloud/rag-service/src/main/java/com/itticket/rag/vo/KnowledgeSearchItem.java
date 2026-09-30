package com.itticket.rag.vo;

/**
 * 知识搜索结果项 —— 契约 AI-004.4（specs/02-ai-api-json-schema.md:174，camelCase）。
 *
 * <p>只允许返回已发布文章的字段与分页元数据，不暴露来源工单（AI-004.4 同条）；
 * 已下线文章不出现（AC-27 · specs/09-prd-spec-test-traceability.md:93）。</p>
 */
public record KnowledgeSearchItem(
        String articleId,
        String versionId,
        String title,
        String summary,
        String categoryId) {
}
