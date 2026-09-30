package com.itticket.rag.vo;

import com.itticket.rag.enums.KnowledgeStatus;

/**
 * ============================================================================
 * 知识生命周期动作结果 (KnowledgeLifecycleResult)
 * ============================================================================
 *
 * <p>索引副作用与状态迁移分离：状态为业务事实，indexStatus 表示 ES 索引的下游结果。
 * 按 RD-006 / RD-008（specs/04-resilience-degradation.md:67 / :93），
 * 索引失败不回滚已经合法的知识状态，而以 PENDING_COMPENSATION 标记待补偿。</p>
 *
 * @param indexStatus NOT_REQUIRED / INDEXED / PARTIAL / OFFLINE_SYNCED / PENDING_COMPENSATION / SKIPPED
 * @author IT工单系统研发组 - RAG专项
 */
public record KnowledgeLifecycleResult(
        String articleId,
        String versionId,
        KnowledgeStatus status,
        String indexStatus,
        String message) {
}
