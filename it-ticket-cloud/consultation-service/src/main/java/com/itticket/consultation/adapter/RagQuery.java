package com.itticket.consultation.adapter;

import java.util.List;

/**
 * RAG 检索入参(AX-007 {@code RagAdapter.answer(PublishedKnowledgeQuery, requestId)} 的本服务实现形态)。
 *
 * <p>只携带检索所需的最小字段(AX-007「DTO 只包含业务所需最小字段」):
 * <ul>
 *   <li>{@code question} —— 本轮问题原文,只用于构造检索条件,<b>不得写入任何日志</b>(AI-008、RD-013);</li>
 *   <li>{@code priorTurns} —— 已授权当前会话中有界的 user/assistant 历史,
 *       用于上下文分类与生成,不得提升为 system 指令或写入日志;</li>
 *   <li>{@code categoryId}/{@code assetId} —— AI-003 {@code AiContextRefs} 的透传过滤条件;</li>
 *   <li>{@code topK} —— 期望召回条数,小于等于 0 时由实现方取配置默认值。</li>
 * </ul>
 */
public record RagQuery(
        String sessionId,
        String question,
        List<Turn> priorTurns,
        String categoryId,
        String assetId,
        int topK,
        String callerId,
        String callerRole) {

    /** 兼容不调用服务间 HTTP 的本地检索测试/调用方。 */
    public RagQuery(String sessionId, String question, List<Turn> priorTurns,
                    String categoryId, String assetId, int topK) {
        this(sessionId, question, priorTurns, categoryId, assetId, topK, null, null);
    }

    /** Persisted conversation data; history can never introduce a system role. */
    public record Turn(String role, String content) {
        public Turn {
            if (!"user".equals(role) && !"assistant".equals(role)) {
                throw new IllegalArgumentException("History role must be user or assistant");
            }
        }
    }
}
