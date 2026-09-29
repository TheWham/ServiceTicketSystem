package com.itticket.consultation.dto;

/**
 * AI-API-003 响应:interactionId 与接收状态。
 * queuedForOptimization=true 表示反馈已持久化为待处理标记，不代表完成脱敏入库。
 *
 * <p>HELPFUL / NOT_HELPFUL / INCORRECT 三种反馈均标记待处理；当前尚无知识域消费者、
 * 脱敏任务或审核后台。未来须先脱敏并经知识管理员审核才能发布，不自动训练或发布。
 */
public record AiFeedbackResponse(
        String interactionId,
        boolean accepted,
        boolean queuedForOptimization) {
}
