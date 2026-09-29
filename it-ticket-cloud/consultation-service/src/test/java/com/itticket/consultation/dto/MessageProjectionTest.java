package com.itticket.consultation.dto;

import com.fasterxml.jackson.databind.JsonNode;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.support.Json;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

class MessageProjectionTest {
    private ConsultationMessage message(String metadata) {
        ConsultationMessage message = new ConsultationMessage();
        message.setMessageId("M1");
        message.setSenderType(MessageSenderType.AI);
        message.setContent("办公 IT 回答");
        message.setCitationJson(metadata);
        return message;
    }

    private JsonNode json(ConsultationMessage message) {
        return Json.read(Json.write(MessageProjection.of(message)), JsonNode.class);
    }

    @Test
    void ac28_history_retains_general_answer_and_feedback_identity() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI1",
                 "replyType":"ANSWER","refusalReason":null,"generalAnswer":true}
                """));
        assertEquals("AI1", result.path("interaction_id").asText());
        assertEquals("ANSWER", result.path("reply_type").asText());
        assertTrue(result.path("general_answer").asBoolean());
        assertEquals(0, result.path("citations").size());
    }

    @Test
    void ac02_history_retains_off_topic_refusal_instead_of_rendering_an_answer() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI2",
                 "replyType":"REFUSE","refusalReason":"OFF_TOPIC","generalAnswer":false}
                """));
        assertEquals("OFF_TOPIC", result.path("refusal_reason").asText());
        assertEquals("REFUSE", result.path("reply_type").asText());
        assertFalse(result.path("general_answer").asBoolean());
    }

    @Test
    void ac01_existing_citation_array_remains_readable() {
        JsonNode result = json(message("""
                [{"articleId":"K1","versionId":"V1","title":"打印机", "score":0.9,"snippet":"检查连接"}]
                """));
        assertEquals("V1", result.path("citations").get(0).path("versionId").asText());
        assertFalse(result.hasNonNull("interaction_id"));
    }

    @Test
    void ac30_withdrawal_never_exposes_answer_metadata() {
        ConsultationMessage message = message("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI1",
                 "replyType":"ANSWER","refusalReason":null,"generalAnswer":true}
                """);
        message.setWithdrawnAt(LocalDateTime.now());
        JsonNode result = json(message);
        assertEquals("该消息已被撤回", result.path("content").asText());
        assertFalse(result.hasNonNull("interaction_id"));
        assertFalse(result.hasNonNull("citations"));
        assertFalse(result.hasNonNull("reply_type"));
        assertFalse(result.path("general_answer").asBoolean());
    }
}
