package com.itticket.ticket.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

import java.time.LocalDateTime;
import java.util.Map;

/** spec 05 Draft 草稿载荷(支持残缺字段,PRD 10.4)。 */
@JsonPropertyOrder({"draft_id", "payload", "last_saved_at", "expires_at"})
public record DraftPayload(
        @JsonProperty("draft_id") String draftId,
        Map<String, Object> payload,
        @JsonProperty("last_saved_at") LocalDateTime lastSavedAt,
        @JsonProperty("expires_at") LocalDateTime expiresAt) {
}
