package com.itticket.consultation.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.enums.AiRefusalReason;

import java.math.BigDecimal;
import java.util.List;

/**
 * AI-003 / AI-004.3。
 * ANSWER 必须有 answerText；知识回答带有效引用，办公 IT 通用建议的 citations 为空。
 * CLARIFY 必须有 answerText，可无引用；
 * REFUSE 必须有 refusalReason 且 answerText 长度为 0(Schema maxLength=0,此处输出 null 省略)。
 */
public record AiChatResponse(
        String sessionId,
        AiReplyType replyType,
        /** REFUSE 时省略(Schema 约束 maxLength=0)。 */
        @JsonInclude(JsonInclude.Include.NON_NULL) String answerText,
        List<KnowledgeCitationDto> citations,
        BigDecimal confidence,
        boolean suggestTransfer,
        /** 仅 REFUSE 时出现。 */
        @JsonInclude(JsonInclude.Include.NON_NULL) AiRefusalReason refusalReason,
        String modelVersion,
        String interactionId,
        /** 建单草稿(人机回环):AI 只产草稿,员工确认后才建单;非建单场景省略。 */
        @JsonInclude(JsonInclude.Include.NON_NULL) TicketDraftDto ticketDraft) {

    /**
     * AI-004.3 把 citations 与 confidence 列为 required(REFUSE 分支同样必须出现),
     * 因此这里兜底成空列表与 0,避免序列化时缺字段。
     */
    public AiChatResponse {
        citations = citations == null ? List.of() : citations;
        confidence = confidence == null ? BigDecimal.ZERO.setScale(4) : confidence;
    }

    /** 向后兼容构造(无建单草稿)。 */
    public AiChatResponse(String sessionId, AiReplyType replyType, String answerText,
                          List<KnowledgeCitationDto> citations, BigDecimal confidence,
                          boolean suggestTransfer, AiRefusalReason refusalReason,
                          String modelVersion, String interactionId) {
        this(sessionId, replyType, answerText, citations, confidence, suggestTransfer,
                refusalReason, modelVersion, interactionId, null);
    }
}
