package com.itticket.consultation.dto;

import java.time.LocalDateTime;

/** 处置结果视图。 */
public record BadCaseReviewView(
        Long id,
        String aiMessageId,
        String sessionId,
        String questionText,
        String refusalReason,
        String decision,
        Long goldenCaseId,
        String reviewNote,
        String reviewedBy,
        LocalDateTime reviewedAt) {
}
