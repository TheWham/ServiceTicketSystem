package com.itticket.consultation.dto;

import com.itticket.consultation.enums.ConsultationStatus;

/** AI-API-001 响应:会话 ID、状态、创建时间(ISO 8601 带时区)。 */
public record ConsultationCreatedResponse(
        String sessionId,
        ConsultationStatus status,
        String createdAt) {
}
