package com.itticket.rag.vo;

import java.math.BigDecimal;

/**
 * ============================================================================
 * 检索命中切片 (RetrievedChunk)
 * ============================================================================
 *
 * <p>对外暴露的检索单元：对接方可直接用 content 拼装 Prompt，用 similarity 做置信度判断，
 * 用 articleId / versionId 生成知识引用。</p>
 *
 * @param chunkId     切片 ID
 * @param articleId   所属知识文章 ID
 * @param versionId   所属知识版本 ID（可追溯到 knowledge_version，DM-004）
 * @param title       切片继承的标题
 * @param snippet     截断后的摘要片段
 * @param content     切片全文
 * @param categoryId  知识分类
 * @param similarity  余弦相似度 [0,1]；纯全文命中（无向量）时为 null
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
        BigDecimal similarity) {
}
