package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.support.Times;

/**
 * OpenAPI 05 ConsultationProjection。
 * 创建者账号用于工程师识别转人工申请人，仍由咨询读取权限控制可见范围。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
@JsonPropertyOrder({"session_id", "status", "category_id", "creator_id", "current_engineer_id", "converted_ticket_id", "created_at"})
public record ConsultationProjection(
        @JsonProperty("session_id") String sessionId,
        String status,
        @JsonProperty("category_id") String categoryId,
        @JsonProperty("creator_id") String creatorId,
        @JsonProperty("current_engineer_id") String currentEngineerId,
        @JsonProperty("converted_ticket_id") String convertedTicketId,
        @JsonProperty("created_at") String createdAt) {

    public static ConsultationProjection of(Consultation consultation) {
        return new ConsultationProjection(
                consultation.getSessionId(),
                consultation.getStatus().getValue(),
                consultation.getCategoryId(),
                consultation.getCreatorId(),
                consultation.getCurrentEngineerId(),
                consultation.getConvertedTicketId(),
                consultation.getCreatedAt() == null ? null : Times.iso(consultation.getCreatedAt()));
    }
}
