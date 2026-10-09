package com.itticket.consultation.adapter;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.*;
import java.math.BigDecimal;
import java.util.List;
/** Answer confidence and retrieval similarity have separate meanings. */
public record RagResult(RagStatus status, AiReplyType replyType, String answerText,
                        List<KnowledgeCitationDto> citations, BigDecimal confidence,
                        AiRefusalReason refusalReason, String modelVersion,
                        List<String> retrievedVersionIds, long latencyMs, String errorClass,
                        boolean generalAnswer, boolean retryableFailure) {
    public static final int CONFIDENCE_SCALE = 4;
    public static final BigDecimal ZERO_CONFIDENCE = BigDecimal.ZERO.setScale(CONFIDENCE_SCALE);
    public static RagResult degraded(RagStatus status, String errorClass, long latencyMs) {
        boolean retryable = status == RagStatus.TIMEOUT ||
                (status == RagStatus.UNAVAILABLE && java.util.Set.of("UNAVAILABLE", "IO", "RATE_LIMITED").contains(errorClass));
        return failure(status, errorClass, retryable, List.of()).withLatency(latencyMs);
    }
    public static RagResult failure(RagStatus status, String errorClass, boolean retryable,
                                    List<String> retrievedVersionIds) {
        return new RagResult(status, AiReplyType.REFUSE, null, List.of(), ZERO_CONFIDENCE,
                null, null, List.copyOf(retrievedVersionIds), 0, errorClass, false, retryable);
    }
    public static RagResult refuse(AiRefusalReason reason, String model, List<String> versions) {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null, List.of(),
                ZERO_CONFIDENCE, reason, model, versions, 0, null, false, false);
    }
    public RagResult withLatency(long latency) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                refusalReason, modelVersion, retrievedVersionIds, latency, errorClass,
                generalAnswer, retryableFailure);
    }
    public RagResult withRetrievedVersionIds(List<String> versions) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                refusalReason, modelVersion, List.copyOf(versions), latencyMs, errorClass,
                generalAnswer, retryableFailure);
    }
}
