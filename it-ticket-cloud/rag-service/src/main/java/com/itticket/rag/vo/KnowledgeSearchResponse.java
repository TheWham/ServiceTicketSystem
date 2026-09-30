package com.itticket.rag.vo;

import java.util.List;

/**
 * 知识搜索响应 —— 契约 AI-004.4（specs/02-ai-api-json-schema.md:174）/
 * AI-API-005（:257）。
 *
 * <p>total 为文章数（按 article_id 折叠去重后的计数），不是切片数。</p>
 */
public record KnowledgeSearchResponse(
        List<KnowledgeSearchItem> items,
        int page,
        int pageSize,
        long total) {
}
