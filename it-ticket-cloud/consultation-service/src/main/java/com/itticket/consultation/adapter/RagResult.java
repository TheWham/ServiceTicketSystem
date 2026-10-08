package com.itticket.consultation.adapter;

import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.enums.AiRefusalReason;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/**
 * RAG 适配器统一出参(AX-007:响应必须带 status、errorClass 等分类信息)。
 *
 * <p>除 {@code status} 外所有字段允许为 null,由上游 {@code AiConsultationService} 决定对外表达:
 * <ul>
 *   <li>{@code status=SUCCESS} 时 {@code replyType} 为 ANSWER 或 REFUSE;ANSWER 必须带
 *       至少一条引用且 {@code answerText} 非空(AI-001、AI-004.3);<b>例外</b>:
 *       {@code generalAnswer=true} 表示回答来自模型通用能力而非知识库命中,
 *       此时 citations 允许为空(冷启动期放宽策略,见 2026-09-29 修订);</li>
 *   <li>{@code status!=SUCCESS} 时由 {@link #degraded} 构造,{@code replyType} 固定为
 *       {@link AiReplyType#REFUSE}、{@code citations} 为空列表、{@code confidence} 为 0,
 *       上游据此映射 {@code AI_UNAVAILABLE} 或 {@code MODEL_UNAVAILABLE} 拒答,
 *       并保留转人工/直接提单入口(RD-006、AI-006);</li>
 *   <li>{@code confidence} 与引用 {@code score} 取值域为 [0,1],统一保留 4 位小数
 *       (AI-002、AI-004.3,与 {@code ai_interaction.confidence DECIMAL(8,4)} 对齐);</li>
 *   <li>{@code knowledgeConflict=true} 表示 topK 内疑似存在互斥结论,上游应按
 *       {@code CONFLICTING_KNOWLEDGE} 拒答(AI-001);</li>
 *   <li>{@code errorClass} 取 AX-007 的错误分类语义(TIMEOUT / UNAVAILABLE / INVALID_RESPONSE 等),
 *       只允许出现分类常量,不得携带堆栈、提示词或知识正文(AI-006、RD-013)。</li>
 * </ul>
 *
 * <p><b>冷启动放宽策略(2026-09-29 修订)</b>新增两个组件:
 * <ul>
 *   <li>{@code generalAnswer}:知识库无命中时,模型基于自身通用能力回答 IT 办公类问题,
 *       回答不携带引用;员工反馈 HELPFUL 后可沉淀入知识库队列;</li>
 *   <li>{@code offTopic}:模型自判问题超出 IT 办公范围,上游据此映射 {@code OFF_TOPIC}
 *       拒答原因,与「知识库无依据」(NO_RELIABLE_KNOWLEDGE) 区分。</li>
 * </ul>
 */
public record RagResult(
        RagStatus status,
        AiReplyType replyType,
        String answerText,
        List<KnowledgeCitationDto> citations,
        BigDecimal confidence,
        boolean knowledgeConflict,
        String modelVersion,
        List<String> retrievedVersionIds,
        long latencyMs,
        String errorClass,
        boolean generalAnswer,
        boolean offTopic,
        boolean highRiskTopic,
        AiRefusalReason refusalReason) {

    public RagResult(RagStatus status, AiReplyType replyType, String answerText,
                     List<KnowledgeCitationDto> citations, BigDecimal confidence,
                     boolean knowledgeConflict, String modelVersion, List<String> retrievedVersionIds,
                     long latencyMs, String errorClass, boolean generalAnswer, boolean offTopic, boolean highRiskTopic) {
        this(status, replyType, answerText, citations, confidence, knowledgeConflict, modelVersion,
                retrievedVersionIds, latencyMs, errorClass, generalAnswer, offTopic, highRiskTopic, null);
    }

    public RagResult(RagStatus status, AiReplyType replyType, String answerText,
                     List<KnowledgeCitationDto> citations, BigDecimal confidence,
                     boolean knowledgeConflict, String modelVersion,
                     List<String> retrievedVersionIds, long latencyMs, String errorClass,
                     boolean generalAnswer, boolean offTopic) {
        this(status, replyType, answerText, citations, confidence, knowledgeConflict,
                modelVersion, retrievedVersionIds, latencyMs, errorClass, generalAnswer, offTopic, false);
    }

    /** 置信度标度:4 位小数,与 DECIMAL(8,4) 存储列一致,避免二进制浮点误差外泄。 */
    public static final int CONFIDENCE_SCALE = 4;

    /** 拒答与降级统一使用的零置信度。 */
    public static final BigDecimal ZERO_CONFIDENCE =
            BigDecimal.ZERO.setScale(CONFIDENCE_SCALE, RoundingMode.UNNECESSARY);

    /** 兼容旧调用方的构造器:非通用回答、非超范围。 */
    public RagResult(RagStatus status, AiReplyType replyType, String answerText,
                     List<KnowledgeCitationDto> citations, BigDecimal confidence,
                     boolean knowledgeConflict, String modelVersion,
                     List<String> retrievedVersionIds, long latencyMs, String errorClass) {
        this(status, replyType, answerText, citations, confidence, knowledgeConflict,
                modelVersion, retrievedVersionIds, latencyMs, errorClass, false, false);
    }

    /** 兼容旧调用方的构造器:非超范围拒答。 */
    public RagResult(RagStatus status, AiReplyType replyType, String answerText,
                     List<KnowledgeCitationDto> citations, BigDecimal confidence,
                     boolean knowledgeConflict, String modelVersion,
                     List<String> retrievedVersionIds, long latencyMs, String errorClass,
                     boolean generalAnswer) {
        this(status, replyType, answerText, citations, confidence, knowledgeConflict,
                modelVersion, retrievedVersionIds, latencyMs, errorClass, generalAnswer, false);
    }

    /**
     * 构造显式降级结果(RD-013:降级结果必须是可判定的有限集合)。
     *
     * @param status     非 SUCCESS 的状态
     * @param errorClass AX-007 错误分类常量
     * @param latencyMs  本次调用耗时
     */
    public static RagResult degraded(RagStatus status, String errorClass, long latencyMs) {
        return new RagResult(status, AiReplyType.REFUSE, null, List.of(), ZERO_CONFIDENCE,
                false, null, List.of(), latencyMs, errorClass, false, false);
    }

    /** 重挂耗时:GuardedRagClient 用整链路耗时(含重试)覆盖适配器自测耗时(RD-010)。 */
    public RagResult withLatency(long totalLatencyMs) {
        return new RagResult(status, replyType, answerText, citations, confidence,
                knowledgeConflict, modelVersion, retrievedVersionIds, totalLatencyMs, errorClass,
                generalAnswer, offTopic, highRiskTopic, refusalReason);
    }
}
