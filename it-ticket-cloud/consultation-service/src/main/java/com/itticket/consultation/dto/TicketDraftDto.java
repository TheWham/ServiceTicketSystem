package com.itticket.consultation.dto;

/**
 * AI 建单草稿(AI-008、人机回环)。
 *
 * <p>AI 只产出草稿,随 {@link AiChatResponse} 返回给员工;员工在前端确认(可编辑)后,
 * 才经 {@code POST /api/v1/consultations/{id}/ticket-draft/confirm} 真正建单。
 * AI 自身无法直接建单——写操作必须由员工显式触发。
 */
public record TicketDraftDto(
        /** 工单标题(已裁剪到配置上限)。 */
        String title,
        /** 分类 ID,如 C_HW_PC;空表示待员工选择。 */
        String category,
        /** 问题描述。 */
        String description,
        /** 建议优先级 HIGH / MEDIUM / LOW。 */
        String priority) {
}
