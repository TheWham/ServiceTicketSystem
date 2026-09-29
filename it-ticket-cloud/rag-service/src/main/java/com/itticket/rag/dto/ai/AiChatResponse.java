package com.itticket.rag.dto.ai;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.itticket.rag.enums.AiRefusalReason;
import com.itticket.rag.enums.AiReplyType;

import java.math.BigDecimal;
import java.util.List;

/**
 * AI 回答响应 —— 契约 AI-003 / AI-004.3（AI-API-002 响应体）。
 *
 * <p>契约约束（由三个静态工厂统一保证，避免调用方手拼出非法形态）：</p>
 * <ul>
 *   <li>必填：sessionId / replyType / citations / confidence / suggestTransfer / modelVersion / interactionId。</li>
 *   <li>ANSWER：answerText 非空且 citations 至少 1 条（AI-001：每个关键结论必须有引用）。</li>
 *   <li>CLARIFY：answerText 非空。</li>
 *   <li>REFUSE：refusalReason 必填，且不输出 answerText（Schema 下 REFUSE 时 answerText 的
 *       minLength=1 与 maxLength=0 互斥，唯一合法形态是字段缺省）。</li>
 * </ul>
 *
 * <p>本模块所有 AI 领域结果（含模型不可用、高风险拦截）均以 HTTP 200 + 结构化拒答返回，
 * 对应 RD-006「返回 AI_UNAVAILABLE/拒答，提供转人工和直接提单」。</p>
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AiChatResponse(
        String sessionId,
        AiReplyType replyType,
        String answerText,
        List<KnowledgeCitation> citations,
        BigDecimal confidence,
        boolean suggestTransfer,
        AiRefusalReason refusalReason,
        String modelVersion,
        String interactionId) {

    /** 正常回答：必须携带至少一条知识引用 */
    public static AiChatResponse answer(String sessionId, String answerText, List<KnowledgeCitation> citations,
                                        BigDecimal confidence, String modelVersion, String interactionId) {
        List<KnowledgeCitation> safeCitations = citations == null ? List.of() : List.copyOf(citations);
        if (safeCitations.isEmpty()) {
            throw new IllegalArgumentException("ANSWER 必须至少携带一条知识引用 (AI-004.3 citations.minItems=1)");
        }
        return new AiChatResponse(sessionId, AiReplyType.ANSWER, answerText, safeCitations,
                confidence, false, null, modelVersion, interactionId);
    }

    /** 澄清：不引用知识，只要求非空文本 */
    public static AiChatResponse clarify(String sessionId, String answerText, BigDecimal confidence,
                                         String modelVersion, String interactionId) {
        return new AiChatResponse(sessionId, AiReplyType.CLARIFY, answerText, List.of(),
                confidence, false, null, modelVersion, interactionId);
    }

    /** 拒答：必须给出结构化原因；不输出 answerText */
    public static AiChatResponse refuse(String sessionId, AiRefusalReason refusalReason, BigDecimal confidence,
                                        boolean suggestTransfer, String modelVersion, String interactionId) {
        return refuse(sessionId, refusalReason, confidence, suggestTransfer, modelVersion, interactionId, List.of());
    }

    /**
     * 拒答并附带检索到的知识引用。
     *
     * <p>用于「检索侧」出口：本模块只交付引用与置信度，回答生成由 AI 客服服务负责，
     * 因此即便检索可靠也不输出 answerText（契约 AI-004.3：REFUSE 时 answerText 缺省）。</p>
     */
    public static AiChatResponse refuse(String sessionId, AiRefusalReason refusalReason, BigDecimal confidence,
                                        boolean suggestTransfer, String modelVersion, String interactionId,
                                        List<KnowledgeCitation> citations) {
        if (refusalReason == null) {
            throw new IllegalArgumentException("REFUSE 必须携带 refusalReason (AI-004.3)");
        }
        return new AiChatResponse(sessionId, AiReplyType.REFUSE, null,
                citations == null ? List.of() : List.copyOf(citations),
                confidence, suggestTransfer, refusalReason, modelVersion, interactionId);
    }
}
