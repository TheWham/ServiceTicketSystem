package com.itticket.consultation.dto;

/**
 * AI-API-003 响应:interactionId 与接收状态。
 * queuedForOptimization=true 表示反馈已持久化为待处理标记，不代表完成脱敏入库。
 *
 * <p>rag-service 消费 HELPFUL 通用回答，关联原始问题后脱敏提审；
 * NOT_HELPFUL / INCORRECT 保留供质量分析，不作为新知识提审。不自动训练或发布。
 */
public record AiFeedbackResponse(
        String interactionId,
        boolean accepted,
        boolean queuedForOptimization) {
}
