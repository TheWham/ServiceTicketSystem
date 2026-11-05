package com.itticket.consultation.adapter;

import com.itticket.consultation.adapter.cache.CacheHitInfo;
import com.itticket.consultation.dto.GovernanceTraceDto;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.dto.TicketDraftDto;
import com.itticket.consultation.enums.*;

import java.math.BigDecimal;
import java.util.List;

/** Answer confidence and retrieval similarity have separate meanings. */
public record RagResult(RagStatus status, AiReplyType replyType, String answerText,
                        List<KnowledgeCitationDto> citations, BigDecimal confidence,
                        AiRefusalReason refusalReason, String modelVersion,
                        List<String> retrievedVersionIds, long latencyMs, String errorClass,
                        boolean generalAnswer, boolean retryableFailure,
                        /** 建单草稿(人机回环);非建单场景为 null。 */
                        TicketDraftDto ticketDraft,
                        /** 成本治理与模型路由全景调用链路 Trace。 */
                        GovernanceTraceDto governanceTrace,
                        /** 语义缓存命中信息(相似度+作用域);实时生成路径为 null。 */
                        CacheHitInfo cacheHit) {

    public static final int CONFIDENCE_SCALE = 4;
    public static final BigDecimal ZERO_CONFIDENCE = BigDecimal.ZERO.setScale(CONFIDENCE_SCALE);

    /** 向后兼容构造(无草稿、无 Trace、无缓存信息)。 */
    public RagResult(RagStatus status, AiReplyType replyType, String answerText,
                     List<KnowledgeCitationDto> citations, BigDecimal confidence,
                     AiRefusalReason refusalReason, String modelVersion,
                     List<String> retrievedVersionIds, long latencyMs, String errorClass,
                     boolean generalAnswer, boolean retryableFailure) {
        this(status, replyType, answerText, citations, confidence, refusalReason, modelVersion,
                retrievedVersionIds, latencyMs, errorClass, generalAnswer, retryableFailure,
                null, null, null);
    }

    /** 向后兼容构造(带草稿、无 Trace、无缓存信息)。 */
    public RagResult(RagStatus status, AiReplyType replyType, String answerText,
                     List<KnowledgeCitationDto> citations, BigDecimal confidence,
                     AiRefusalReason refusalReason, String modelVersion,
                     List<String> retrievedVersionIds, long latencyMs, String errorClass,
                     boolean generalAnswer, boolean retryableFailure, TicketDraftDto ticketDraft) {
        this(status, replyType, answerText, citations, confidence, refusalReason, modelVersion,
                retrievedVersionIds, latencyMs, errorClass, generalAnswer, retryableFailure,
                ticketDraft, null, null);
    }

    /** 向后兼容构造(带草稿与 Trace、无缓存信息)。 */
    public RagResult(RagStatus status, AiReplyType replyType, String answerText,
                     List<KnowledgeCitationDto> citations, BigDecimal confidence,
                     AiRefusalReason refusalReason, String modelVersion,
                     List<String> retrievedVersionIds, long latencyMs, String errorClass,
                     boolean generalAnswer, boolean retryableFailure, TicketDraftDto ticketDraft,
                     GovernanceTraceDto governanceTrace) {
        this(status, replyType, answerText, citations, confidence, refusalReason, modelVersion,
                retrievedVersionIds, latencyMs, errorClass, generalAnswer, retryableFailure,
                ticketDraft, governanceTrace, null);
    }

    public static RagResult degraded(RagStatus status, String errorClass, long latencyMs) {
        boolean retryable = status == RagStatus.TIMEOUT ||
                (status == RagStatus.UNAVAILABLE && java.util.Set.of("UNAVAILABLE", "IO", "RATE_LIMITED").contains(errorClass));
        return failure(status, errorClass, retryable, List.of()).withLatency(latencyMs);
    }

    public static RagResult failure(RagStatus status, String errorClass, boolean retryable,
                                    List<String> retrievedVersionIds) {
        return new RagResult(status, AiReplyType.REFUSE, null, List.of(), ZERO_CONFIDENCE,
                null, null, List.copyOf(retrievedVersionIds), 0, errorClass, false, retryable,
                null, null, null);
    }

    public static RagResult refuse(AiRefusalReason reason, String model, List<String> versions) {
        return refuse(reason, model, versions, ZERO_CONFIDENCE);
    }

    /** 检索不足类拒答透传真实最高命中分(检索类拒答的 topScore);分类拒答无评分语义,保持 ZERO。 */
    public static RagResult refuse(AiRefusalReason reason, String model, List<String> versions,
                                   BigDecimal confidence) {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null, List.of(),
                confidence == null ? ZERO_CONFIDENCE : confidence.setScale(CONFIDENCE_SCALE,
                        java.math.RoundingMode.HALF_UP), reason, model, versions, 0, null, false, false,
                null, null, null);
    }

    public RagResult withLatency(long latency) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                refusalReason, modelVersion, retrievedVersionIds, latency, errorClass,
                generalAnswer, retryableFailure, ticketDraft, governanceTrace, cacheHit);
    }

    public RagResult withRetrievedVersionIds(List<String> versions) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                refusalReason, modelVersion, List.copyOf(versions), latencyMs, errorClass,
                generalAnswer, retryableFailure, ticketDraft, governanceTrace, cacheHit);
    }

    /** 附加建单草稿(AI 只产草稿,不落库)。 */
    public RagResult withTicketDraft(TicketDraftDto draft) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                refusalReason, modelVersion, retrievedVersionIds, latencyMs, errorClass,
                generalAnswer, retryableFailure, draft, governanceTrace, cacheHit);
    }

    /** 附加治理调用链路 Trace。 */
    public RagResult withGovernanceTrace(GovernanceTraceDto trace) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                refusalReason, modelVersion, retrievedVersionIds, latencyMs, errorClass,
                generalAnswer, retryableFailure, ticketDraft, trace, cacheHit);
    }

    /** 附加语义缓存命中信息(实时路径不加,保持 null)。 */
    public RagResult withCacheHit(double similarity, String scope) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                refusalReason, modelVersion, retrievedVersionIds, latencyMs, errorClass,
                generalAnswer, retryableFailure, ticketDraft, governanceTrace,
                new CacheHitInfo(similarity, scope));
    }
}
