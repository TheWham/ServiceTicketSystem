package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.itticket.consultation.enums.ConsultationStatus;

/**
 * AI-003 / AI-004.4 转人工响应。Schema 约束 status 恒为 WAITING_ENGINEER,
 * estimatedWaitSeconds 非负;未分配到工程师时 assignmentId 省略。
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TransferResponse(
        String sessionId,
        ConsultationStatus status,
        String assignmentId,
        long estimatedWaitSeconds) {
}
