package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * AI-007 标准流式事件包络 Schema (docs/specs/10-model-rag-integration.md line 230)。
 *
 * {
 *   "eventId": "evt_...",
 *   "sessionId": "cs_...",
 *   "sequence": 1,
 *   "eventType": "answer_delta" | "citation" | "answer_completed" | "refusal" | "error",
 *   "data": { ... }
 * }
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AiStreamEvent {

    @JsonProperty("eventId")
    private String eventId;

    @JsonProperty("sessionId")
    private String sessionId;

    @JsonProperty("sequence")
    private Integer sequence;

    @JsonProperty("eventType")
    private String eventType;

    @JsonProperty("data")
    private Map<String, Object> data;

    public static AiStreamEvent delta(String sessionId, int seq, String delta) {
        return AiStreamEvent.builder()
                .eventId("evt_" + System.currentTimeMillis() + "_" + seq)
                .sessionId(sessionId)
                .sequence(seq)
                .eventType("answer_delta")
                .data(Map.of("delta", delta))
                .build();
    }

    public static AiStreamEvent reasoning(String sessionId, int seq, String delta) {
        return AiStreamEvent.builder()
                .eventId("evt_" + System.currentTimeMillis() + "_" + seq)
                .sessionId(sessionId)
                .sequence(seq)
                .eventType("reasoning_delta")
                .data(Map.of("delta", delta))
                .build();
    }

    public static AiStreamEvent completed(String sessionId, int seq, Map<String, Object> fullData) {
        return AiStreamEvent.builder()
                .eventId("evt_" + System.currentTimeMillis() + "_" + seq)
                .sessionId(sessionId)
                .sequence(seq)
                .eventType("answer_completed")
                .data(fullData)
                .build();
    }

    public static AiStreamEvent error(String sessionId, int seq, String code, String message) {
        return AiStreamEvent.builder()
                .eventId("evt_" + System.currentTimeMillis() + "_" + seq)
                .sessionId(sessionId)
                .sequence(seq)
                .eventType("error")
                .data(Map.of("code", code, "message", message))
                .build();
    }

    public static AiStreamEvent refusal(String sessionId, int seq, String reason) {
        return AiStreamEvent.builder()
                .eventId("evt_" + System.currentTimeMillis() + "_" + seq)
                .sessionId(sessionId)
                .sequence(seq)
                .eventType("refusal")
                .data(Map.of("reason", reason))
                .build();
    }
}
