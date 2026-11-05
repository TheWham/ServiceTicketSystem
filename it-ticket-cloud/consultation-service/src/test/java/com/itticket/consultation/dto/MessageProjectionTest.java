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

    /** 建单草稿随 AI 消息元数据回放：预填接口据此读取，避免再从完整时间线拼接上下文 */
    @Test
    void ticket_draft_is_replayed_from_ai_message_metadata() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI3",
                 "replyType":"ANSWER","generalAnswer":false,
                 "ticketDraft":{"title":"vpn连不上","category":"C_NET",
                                "description":"vpn连不上","priority":"MEDIUM"}}
                """));
        JsonNode draft = result.path("ticket_draft");
        assertEquals("vpn连不上", draft.path("title").asText());
        assertEquals("vpn连不上", draft.path("description").asText());
        assertEquals("C_NET", draft.path("category").asText());
        assertEquals("MEDIUM", draft.path("priority").asText());
    }

    /** 无草稿的普通答复不得凭空渲染 ticket_draft 字段 */
    @Test
    void ticket_draft_absent_when_metadata_has_none() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI4",
                 "replyType":"ANSWER","generalAnswer":true}
                """));
        assertFalse(result.hasNonNull("ticket_draft"));
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

    /**
     * 建单草稿随消息落库：刷新页面后草稿卡必须还在。
     *
     * <p>原先草稿只活在本次对话的消息对象里，历史回显读不到它 —— 员工刷新一下就看到
     * "AI 已拟好草稿"的正文却没有任何卡片可点。
     */
    @Test
    void history_retains_ticket_draft_so_the_card_survives_a_reload() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI1","replyType":"ANSWER",
                 "refusalReason":null,"generalAnswer":true,
                 "ticketDraft":{"title":"vpn连不上","category":"C_NET",
                                "description":"连接公司VPN提示认证失败","priority":"MEDIUM"}}
                """));
        JsonNode draft = result.path("ticket_draft");
        assertTrue(draft.isObject(), "历史消息必须带出草稿，否则刷新后卡片消失");
        assertEquals("vpn连不上", draft.path("title").asText());
        assertEquals("C_NET", draft.path("category").asText());
        assertEquals("连接公司VPN提示认证失败", draft.path("description").asText());
        assertEquals("MEDIUM", draft.path("priority").asText());
    }

    /** 无草稿的消息不输出该字段 —— 不给前端塞一个恒为 null 的键（老数据也没有这个键） */
    @Test
    void history_omits_ticket_draft_when_absent() {
        JsonNode noKey = json(message("""
                {"schemaVersion":1,"citations":[],"interactionId":"AI1","replyType":"ANSWER","generalAnswer":false}
                """));
        assertFalse(noKey.hasNonNull("ticket_draft"), "没有草稿就不该出现该字段");

        JsonNode nullDraft = json(message("""
                {"schemaVersion":1,"citations":[],"ticketDraft":null,"replyType":"ANSWER"}
                """));
        assertFalse(nullDraft.hasNonNull("ticket_draft"));
    }

    /** 空壳草稿（标题与描述都空）视为没有草稿：别让前端渲染出一张没有内容、点不开的卡 */
    @Test
    void blank_ticket_draft_is_treated_as_absent() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"replyType":"ANSWER",
                 "ticketDraft":{"title":"","category":"C_NET","description":"","priority":null}}
                """));
        assertFalse(result.hasNonNull("ticket_draft"));
    }

    /** 撤回消息的草稿一并抹除（与 AC-30 同一口径：撤回后不留下任何可操作内容） */
    @Test
    void withdrawal_also_removes_the_ticket_draft() {
        ConsultationMessage message = message("""
                {"schemaVersion":1,"citations":[],"replyType":"ANSWER",
                 "ticketDraft":{"title":"vpn连不上","category":"C_NET","description":"提示认证失败","priority":"MEDIUM"}}
                """);
        message.setWithdrawnAt(LocalDateTime.now());
        assertFalse(json(message).hasNonNull("ticket_draft"));
    }

    /** 草稿结构损坏时只丢草稿，正文与答复类型照常 —— 草稿不该把整条消息一起拖没 */
    @Test
    void malformed_ticket_draft_does_not_break_the_message() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"replyType":"ANSWER","ticketDraft":"这不是对象"}
                """));
        assertEquals("办公 IT 回答", result.path("content").asText());
        assertEquals("ANSWER", result.path("reply_type").asText());
        assertFalse(result.hasNonNull("ticket_draft"));
    }

    /** 思考过程与耗时随消息落库：刷新后思考步骤、耗时与思维链 100% 完整复现 */
    @Test
    void history_retains_thought_stages_and_duration_so_it_survives_reload() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"replyType":"ANSWER",
                 "thoughtStages":["模型路由：已匹配标准档位","主管规划排障链路","排障方案合成"],
                 "reasoningContent":"分析用户电脑无法连接WiFi的原因...",
                 "thinkingDuration":4}
                """));
        assertEquals("ANSWER", result.path("reply_type").asText());
        assertTrue(result.hasNonNull("thought_stages"));
        assertEquals(3, result.path("thought_stages").size());
        assertEquals("模型路由：已匹配标准档位", result.path("thought_stages").get(0).asText());
        assertEquals("主管规划排障链路", result.path("thought_stages").get(1).asText());
        assertEquals("分析用户电脑无法连接WiFi的原因...", result.path("reasoning_content").asText());
        assertEquals(4, result.path("thinking_duration").asInt());
    }

    @Test
    void history_omits_thought_stages_when_absent() {
        JsonNode result = json(message("""
                {"schemaVersion":1,"citations":[],"replyType":"ANSWER"}
                """));
        assertFalse(result.hasNonNull("thought_stages"));
        assertFalse(result.hasNonNull("reasoning_content"));
        assertFalse(result.hasNonNull("thinking_duration"));
    }
}