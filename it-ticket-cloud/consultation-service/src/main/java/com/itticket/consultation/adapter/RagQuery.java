package com.itticket.consultation.adapter;

import java.util.List;

/**
 * RAG 检索入参(AX-007 {@code RagAdapter.answer(PublishedKnowledgeQuery, requestId)} 的本服务实现形态)。
 *
 * <p>只携带检索所需的最小字段(AX-007「DTO 只包含业务所需最小字段」):
 * <ul>
 *   <li>{@code question} —— 本轮问题原文,只用于构造检索条件,<b>不得写入任何日志</b>(AI-008、RD-013);</li>
 *   <li>{@code priorTurns} —— 上文轮次,仅供实现方裁剪上下文使用;
 *       本地实现(KnowledgeRagAdapter)不使用它,也不落库、不外发;</li>
 *   <li>{@code categoryId}/{@code assetId} —— AI-003 {@code AiContextRefs} 的透传过滤条件;</li>
 *   <li>{@code topK} —— 期望召回条数,小于等于 0 时由实现方取配置默认值。</li>
 * </ul>
 */
public record RagQuery(
        String sessionId,
        String question,
        List<String> priorTurns,
        String categoryId,
        String assetId,
        int topK) {
}
