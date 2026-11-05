package com.itticket.consultation.adapter.generation;

import com.itticket.consultation.dto.GovernanceTraceDto;
import com.itticket.consultation.dto.TicketDraftDto;
import com.itticket.consultation.enums.*;

import java.math.BigDecimal;
import java.util.List;

/**
 * 生成结果。
 *
 * <p>{@code ticketDraft} 是人机回环的载体:AI 只产草稿(不落库),随响应返回员工确认后才建单。
 * 非建单场景为 null。
 * <p>{@code governanceTrace} 是 Model Router 成本治理全景调用链路。
 */
public record GenerationResult(AiReplyType replyType, String answerText,
        List<String> usedVersionIds, BigDecimal confidence, AiRefusalReason refusalReason,
        String modelVersion, TicketDraftDto ticketDraft, GovernanceTraceDto governanceTrace) {
    public GenerationResult { usedVersionIds = List.copyOf(usedVersionIds); }

    public GenerationResult(AiReplyType replyType, String answerText, List<String> usedVersionIds,
                            BigDecimal confidence, AiRefusalReason refusalReason, String modelVersion,
                            TicketDraftDto ticketDraft) {
        this(replyType, answerText, usedVersionIds, confidence, refusalReason, modelVersion, ticketDraft, null);
    }

    /** 无草稿场景的便捷构造(向后兼容)。 */
    public GenerationResult(AiReplyType replyType, String answerText, List<String> usedVersionIds,
                            BigDecimal confidence, AiRefusalReason refusalReason, String modelVersion) {
        this(replyType, answerText, usedVersionIds, confidence, refusalReason, modelVersion, null, null);
    }
}
