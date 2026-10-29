package com.itticket.consultation.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** 拒答案例列表项(管理端)。AI 消息 refusalReason 提取自 citation_json。 */
public record RefusalCaseItem(
        String messageId,
        String sessionId,
        String questionText,
        String refusalReason,
        BigDecimal confidence,
        LocalDateTime sentAt,
        String reviewStatus,
        String decision) {
}
