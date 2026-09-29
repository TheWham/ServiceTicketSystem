package com.itticket.rag.vo;

import java.math.BigDecimal;

/**
 * ============================================================================
 * 检索命中切片 (RetrievedChunk)
 * ============================================================================
 *
 * <p>契约 MR-004：检索器只返回 PUBLISHED 版本，并携带
 * {@code articleId / versionId / score / snippet / indexVersion}。
 * content 供对接方拼装 Prompt；score 为余弦相似度 [0,1]。</p>
 *
 * @param chunkId      切片 ID
 * @param articleId    所属知识文章 ID
 * @param versionId    所属知识版本 ID（可追溯到 knowledge_version.version_id，DM-004）
 * @param title        切片继承的标题
 * @param snippet      截断后的摘要片段（≤1000）
 * @param content      切片全文
 * @param categoryId   知识分类
 * @param score        余弦相似度 [0,1]；纯全文命中（无向量）时为 null
 * @param indexVersion 该切片所属的索引版本（ES 文档 index_version 字段，MR-011）
 * @author IT工单系统研发组 - RAG专项
 */
public record RetrievedChunk(
        String chunkId,
        String articleId,
        String versionId,
        String title,
        String snippet,
        String content,
        String categoryId,
        BigDecimal score,
        String indexVersion) {
}
