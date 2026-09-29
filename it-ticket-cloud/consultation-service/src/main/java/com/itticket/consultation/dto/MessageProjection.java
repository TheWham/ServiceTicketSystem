package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;
import com.fasterxml.jackson.databind.JsonNode;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.support.Times;

import java.util.List;

/**
 * 咨询消息投影(OpenAPI 05 MessageProjection 的扩展)。
 *
 * <p><b>契约缺口 G11</b>:05 的 MessageProjection 只声明 message_id / sent_at / withdrawn_at
 * 且 additionalProperties=false,按字面实现的话聊天记录读不出正文,
 * 而 PRD 5.2 与 13.1 明确要求"普通聊天正文"对本人和当前负责人可见 —— 两者冲突。
 * 这里按产品需求补正文及 AI 回答元数据，已回写 05；citation_json 兼容历史引用数组。
 *
 * <p>撤回消息只返回占位文案,不返回原文:PRD 5.2 规定撤回原文仅平台管理员的专用审计视图可读。
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
@JsonPropertyOrder({"message_id", "sender_type", "content", "citations",
        "interaction_id", "reply_type", "refusal_reason", "general_answer", "sent_at", "withdrawn_at"})
public record MessageProjection(
        @JsonProperty("message_id") String messageId,
        @JsonProperty("sender_type") String senderType,
        String content,
        @JsonInclude(JsonInclude.Include.NON_NULL) List<KnowledgeCitationDto> citations,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("interaction_id") String interactionId,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("reply_type") String replyType,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("refusal_reason") String refusalReason,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("general_answer") Boolean generalAnswer,
        @JsonProperty("sent_at") String sentAt,
        @JsonProperty("withdrawn_at") String withdrawnAt) {

    private static final String WITHDRAWN_PLACEHOLDER = "该消息已被撤回";

    public static MessageProjection of(ConsultationMessage message) {
        boolean withdrawn = message.getWithdrawnAt() != null;
        Metadata metadata = withdrawn ? Metadata.EMPTY : parseMetadata(message.getCitationJson());
        return new MessageProjection(
                message.getMessageId(),
                message.getSenderType() == null ? null : message.getSenderType().getValue(),
                withdrawn ? WITHDRAWN_PLACEHOLDER : message.getContent(),
                metadata.citations(),
                metadata.interactionId(),
                metadata.replyType(),
                metadata.refusalReason(),
                metadata.generalAnswer(),
                Times.iso(message.getSentAt()),
                Times.iso(message.getWithdrawnAt()));
    }

    private record Metadata(List<KnowledgeCitationDto> citations, String interactionId,
                            String replyType, String refusalReason, Boolean generalAnswer) {
        private static final Metadata EMPTY = new Metadata(null, null, null, null, null);
    }

    private static Metadata parseMetadata(String citationJson) {
        if (citationJson == null || citationJson.isBlank()) {
            return Metadata.EMPTY;
        }
        try {
            JsonNode root = Json.read(citationJson, JsonNode.class);
            if (root.isArray()) {
                return new Metadata(readCitations(root), null, null, null, null);
            }
            if (!root.isObject() || root.path("schemaVersion").asInt() != 1) return Metadata.EMPTY;
            return new Metadata(readCitations(root.path("citations")),
                    text(root, "interactionId"), text(root, "replyType"), text(root, "refusalReason"),
                    root.path("generalAnswer").isBoolean() ? root.path("generalAnswer").asBoolean() : null);
        } catch (RuntimeException e) {
            // 旧数据或元数据损坏不影响正文展示，也不猜测引用或交互 ID。
            return Metadata.EMPTY;
        }
    }

    private static List<KnowledgeCitationDto> readCitations(JsonNode node) {
        return node.isArray() ? List.of(Json.read(node.toString(), KnowledgeCitationDto[].class)) : null;
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.path(field);
        return value.isTextual() ? value.asText() : null;
    }
}
