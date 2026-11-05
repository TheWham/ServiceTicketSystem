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
@JsonPropertyOrder({"message_id", "sender_type", "content", "attachments", "citations",
        "interaction_id", "reply_type", "refusal_reason", "general_answer", "ticket_draft", "governance_trace",
        "sent_at", "withdrawn_at"})
public record MessageProjection(
        @JsonProperty("message_id") String messageId,
        @JsonProperty("sender_type") String senderType,
        String content,
        List<AttachmentProjection> attachments,
        @JsonInclude(JsonInclude.Include.NON_NULL) List<KnowledgeCitationDto> citations,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("interaction_id") String interactionId,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("reply_type") String replyType,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("refusal_reason") String refusalReason,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("general_answer") Boolean generalAnswer,
        /**
         * AI 拟好的建单草稿，随消息一起落库（元数据里的 {@code ticketDraft}）。
         *
         * <p>之所以要持久化：草稿卡原先只活在本次对话的消息对象里，历史消息映射读不到它，
         * 于是**刷新页面卡片就没了** —— 员工看到"AI 已拟好草稿"的正文却无从点起。
         */
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("ticket_draft") TicketDraftDto ticketDraft,
        @JsonInclude(JsonInclude.Include.NON_NULL) @JsonProperty("governance_trace") GovernanceTraceDto governanceTrace,
        @JsonProperty("sent_at") String sentAt,
        @JsonProperty("withdrawn_at") String withdrawnAt) {

    public MessageProjection {
        attachments = attachments == null ? List.of() : List.copyOf(attachments);
    }

    private static final String WITHDRAWN_PLACEHOLDER = "该消息已被撤回";

    public static MessageProjection of(ConsultationMessage message) {
        boolean withdrawn = message.getWithdrawnAt() != null;
        Metadata metadata = withdrawn ? Metadata.EMPTY : parseMetadata(message.getCitationJson());
        return new MessageProjection(
                message.getMessageId(),
                message.getSenderType() == null ? null : message.getSenderType().getValue(),
                withdrawn ? WITHDRAWN_PLACEHOLDER : message.getContent(),
                metadata.attachments(),
                metadata.citations(),
                metadata.interactionId(),
                metadata.replyType(),
                metadata.refusalReason(),
                metadata.generalAnswer(),
                metadata.ticketDraft(),
                metadata.governanceTrace(),
                Times.iso(message.getSentAt()),
                Times.iso(message.getWithdrawnAt()));
    }

    private record Metadata(List<KnowledgeCitationDto> citations, String interactionId,
                            String replyType, String refusalReason, Boolean generalAnswer,
                            List<AttachmentProjection> attachments, TicketDraftDto ticketDraft,
                            GovernanceTraceDto governanceTrace) {
        private static final Metadata EMPTY =
                new Metadata(null, null, null, null, null, List.of(), null, null);
    }

    private static Metadata parseMetadata(String citationJson) {
        if (citationJson == null || citationJson.isBlank()) {
            return Metadata.EMPTY;
        }
        try {
            JsonNode root = Json.read(citationJson, JsonNode.class);
            if (root.isArray()) {
                return new Metadata(readCitations(root), null, null, null, null, List.of(), null, null);
            }
            if (!root.isObject() || root.path("schemaVersion").asInt() != 1) return Metadata.EMPTY;
            return new Metadata(readCitations(root.path("citations")),
                    text(root, "interactionId"), text(root, "replyType"), text(root, "refusalReason"),
                    root.path("generalAnswer").isBoolean() ? root.path("generalAnswer").asBoolean() : null,
                    readAttachments(root.path("attachments")),
                    readTicketDraft(root.path("ticketDraft")),
                    readGovernanceTrace(root.path("governanceTrace")));
        } catch (RuntimeException e) {
            // 旧数据或元数据损坏不影响正文展示，也不猜测引用、交互 ID 或草稿。
            return Metadata.EMPTY;
        }
    }

    /**
     * 读取元数据里的建单草稿。缺字段或结构不对一律返回 null —— 草稿只是"能不能点"的前提，
     * 它坏了不该把整条消息的正文和引用一起拖没。
     */
    private static TicketDraftDto readTicketDraft(JsonNode node) {
        if (!node.isObject()) return null;
        try {
            TicketDraftDto draft = Json.read(node.toString(), TicketDraftDto.class);
            boolean blank = draft == null
                    || ((draft.title() == null || draft.title().isBlank())
                        && (draft.description() == null || draft.description().isBlank()));
            return blank ? null : draft;
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static List<KnowledgeCitationDto> readCitations(JsonNode node) {
        return node.isArray() ? List.of(Json.read(node.toString(), KnowledgeCitationDto[].class)) : null;
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.path(field);
        return value.isTextual() ? value.asText() : null;
    }

    private static List<AttachmentProjection> readAttachments(JsonNode node) {
        return node.isArray() ? List.of(Json.read(node.toString(), AttachmentProjection[].class)) : List.of();
    }
    private static GovernanceTraceDto readGovernanceTrace(JsonNode node) {
        if (!node.isObject()) return null;
        try {
            return Json.read(node.toString(), GovernanceTraceDto.class);
        } catch (RuntimeException e) {
            return null;
        }
    }
}
