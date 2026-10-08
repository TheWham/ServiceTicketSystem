package com.itticket.consultation.dto;

import com.fasterxml.jackson.databind.JsonNode;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.support.Json;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 咨询消息投影（MessageProjection）的历史回显契约：
 *  - citation_json 列同时并存“旧格式纯数组”和“新格式带 schemaVersion 的对象”，
 *    投影必须两种都能读（AC-01），且统一映射为 snake_case 输出键；
 *  - 通用答复 / 拒答的答复类型、拒答原因、交互 ID 必须在历史里可回放（AC-02/AC-28）；
 *  - 已撤回消息：正文替换为占位文案，且交互元数据全部抹除（AC-30 隐私要求）。
 */
class MessageProjectionTest {

    /** 造一条 AI 答复消息，citation_json 内容由各用例注入不同历史格式 */
    private ConsultationMessage message(String metadata) {
        ConsultationMessage message = new ConsultationMessage();
        message.setMessageId("M1");
        message.setSenderType(MessageSenderType.AI);
        message.setContent("办公 IT 回答");
        message.setCitationJson(metadata);
        return message;
    }

    /** 走一遍真实序列化管线：Projection -> JSON 字符串 -> 树（等价于接口响应的最终形态） */
    private JsonNode json(ConsultationMessage message) {
        return Json.read(Json.write(MessageProjection.of(message)), JsonNode.class);
    }

    /** AC-28：历史消息要保留“这是 AI 通用答复”身份——交互 ID / 答复类型 / generalAnswer 标记都可回显 */
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

    /** AC-02：拒答消息在历史里必须仍呈现为拒答（含拒答原因），不允许渲染成一条正常答复 */
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

    /** AC-01：旧数据 citation_json 是纯数组（无 schemaVersion），必须可读，且有引用时无交互 ID */
    @Test
    void ac01_existing_citation_array_remains_readable() {
        JsonNode result = json(message("""
                [{"articleId":"K1","versionId":"V1","title":"打印机", "score":0.9,"snippet":"检查连接"}]
                """));
        assertEquals("V1", result.path("citations").get(0).path("versionId").asText());
        assertFalse(result.hasNonNull("interaction_id"));
    }

    /** AC-30：撤回的消息正文替换为占位文案；交互 ID / 引用 / 答复类型等元数据一律不外泄 */
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