package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import com.itticket.consultation.entity.Consultation;

/**
 * OpenAPI 05 ConsultationProjection。
 * 创建者账号用于工程师识别转人工申请人，仍由咨询读取权限控制可见范围。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
@JsonPropertyOrder({"session_id", "status", "creator_id", "current_engineer_id", "converted_ticket_id"})
public record ConsultationProjection(
        @JsonProperty("session_id") String sessionId,
        String status,
        @JsonProperty("creator_id") String creatorId,
        @JsonProperty("current_engineer_id") String currentEngineerId,
        @JsonProperty("converted_ticket_id") String convertedTicketId) {

    public static ConsultationProjection of(Consultation consultation) {
        return new ConsultationProjection(
                consultation.getSessionId(),
                consultation.getStatus().getValue(),
                consultation.getCreatorId(),
                consultation.getCurrentEngineerId(),
                consultation.getConvertedTicketId());
    }
}
