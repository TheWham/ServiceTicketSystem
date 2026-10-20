package com.itticket.consultation.adapter.generation;
import com.itticket.consultation.dto.TicketDraftDto;
import com.itticket.consultation.enums.*;
import java.math.BigDecimal;
import java.util.List;
/**
 * 生成结果。
 *
 * <p>{@code ticketDraft} 是人机回环的载体:AI 只产草稿(不落库),随响应返回员工确认后才建单。
 * 非建单场景为 null。
 */
public record GenerationResult(AiReplyType replyType, String answerText,
        List<String> usedVersionIds, BigDecimal confidence, AiRefusalReason refusalReason,
        String modelVersion, TicketDraftDto ticketDraft) {
    public GenerationResult { usedVersionIds = List.copyOf(usedVersionIds); }

    /** 无草稿场景的便捷构造(向后兼容)。 */
    public GenerationResult(AiReplyType replyType, String answerText, List<String> usedVersionIds,
                            BigDecimal confidence, AiRefusalReason refusalReason, String modelVersion) {
        this(replyType, answerText, usedVersionIds, confidence, refusalReason, modelVersion, null);
    }
}