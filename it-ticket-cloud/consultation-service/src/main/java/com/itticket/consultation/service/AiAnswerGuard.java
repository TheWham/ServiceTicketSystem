package com.itticket.consultation.service;

import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;

import java.math.BigDecimal;
import java.util.List;
import java.util.function.BiPredicate;

/**
 * AI 输出守卫(AI-001、AI-008)。
 *
 * <p>AI-008 要求模型输出必须先通过 Schema、引用存在性、知识版本仍为 PUBLISHED 和高风险规则校验,
 * 才能返回客户端。本类是这道闸门的唯一实现,是纯函数,不访问数据库也不写库:
 * 知识版本是否仍然发布由调用方以 {@code citationValidator} 注入,便于单测。
 *
 * <p>只有正常检索且无相关依据的办公 IT 问题，才允许进入通用生成。
 * 适配器标记 {@code generalAnswer=true} 的回答
 * 允许无引用放行,但置信度必须达标且建议转人工入口保持可见;
 * 领域、风险、检索与生成的拒答结论统一通过 {@code refusalReason} 保留，高风险操作转人工。
 * 只要使用知识引用就严格复核；检索到不相关资料不强制挂载来源。
 *
 * <p>判定优先级(先命中先返回,保证降级原因唯一且可判定 —— RD-013):
 * <ol>
 *   <li>评测未达上线门槛 → POLICY_BLOCKED(PRD 17.3);</li>
 *   <li>依赖超时/不可用/断路器打开 → MODEL_UNAVAILABLE(RD-006);</li>
 *   <li>模型输出不合 Schema → NO_RELIABLE_KNOWLEDGE，不透传非法输出；</li>
 *   <li>显式拒答原因原样保留；缺少原因的 REFUSE → NO_RELIABLE_KNOWLEDGE;</li>
 *   <li>范围不明确的无引用追问 → CLARIFY;</li>
 *   <li>通用能力回答:置信度达标即放行(无引用,冷启动修订);</li>
 *   <li>知识库回答:引用缺失或已不是当前发布版本 → NO_RELIABLE_KNOWLEDGE;</li>
 *   <li>置信度不足 → LOW_CONFIDENCE。</li>
 * </ol>
 */
public final class AiAnswerGuard {

    private AiAnswerGuard() {
    }

    /**
     * 守卫结论。
     *
     * @param replyType      对外回复类型
     * @param answerText     ANSWER/CLARIFY 的正文;REFUSE 时为 null(Schema 约束 maxLength=0)
     * @param citations      通过校验的引用;通用能力回答为空列表
     * @param confidence     置信度
     * @param refusalReason  拒答原因;非 REFUSE 时为 null
     * @param suggestTransfer 是否建议转人工
     */
    public record Verdict(AiReplyType replyType,
                          String answerText,
                          List<KnowledgeCitationDto> citations,
                          BigDecimal confidence,
                          AiRefusalReason refusalReason,
                          boolean suggestTransfer) {

        static Verdict refuse(AiRefusalReason reason, BigDecimal confidence) {
            return new Verdict(AiReplyType.REFUSE, null, List.of(),
                    confidence == null ? RagResult.ZERO_CONFIDENCE : confidence, reason, true);
        }
    }

    /**
     * @param result           受保护调用的结果
     * @param properties       AI 配置
     * @param citationValidator (articleId, versionId) → 是否仍为 PUBLISHED 的当前版本
     */
    public static Verdict evaluate(RagResult result,
                                   ConsultationProperties.Ai properties,
                                   BiPredicate<String, String> citationValidator) {
        // 1. AI 评测未达上线门槛:只关闭综合回答,其余入口不受影响(PRD 17.3、RD-006)
        if (!properties.isAnswerEnabled()) {
            return Verdict.refuse(AiRefusalReason.POLICY_BLOCKED, RagResult.ZERO_CONFIDENCE);
        }
        // 2. 缺少调用结果或状态时按依赖不可用处理。
        if (result == null || result.status() == null) {
            return Verdict.refuse(AiRefusalReason.MODEL_UNAVAILABLE, RagResult.ZERO_CONFIDENCE);
        }
        // 3. 超时、不可用、断路器打开
        if (result.status() == RagStatus.TIMEOUT || result.status() == RagStatus.UNAVAILABLE) {
            return Verdict.refuse(AiRefusalReason.MODEL_UNAVAILABLE, RagResult.ZERO_CONFIDENCE);
        }
        // 4. 非法输出不能转为通用回答绕过协议校验。
        if (result.status() == RagStatus.INVALID_RESPONSE) {
            return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, RagResult.ZERO_CONFIDENCE);
        }
        // 5. 保留上游明确的领域、风险、检索或生成拒答原因。
        if (result.replyType() == null) {
            return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, RagResult.ZERO_CONFIDENCE);
        }
        if (result.refusalReason() != null) {
            return Verdict.refuse(result.refusalReason(), result.refusalReason() == AiRefusalReason.HIGH_RISK_TOPIC
                    ? RagResult.ZERO_CONFIDENCE : result.confidence());
        }
        if (result.replyType() == AiReplyType.REFUSE) {
            return Verdict.refuse(result.refusalReason() == null
                    ? AiRefusalReason.NO_RELIABLE_KNOWLEDGE : result.refusalReason(), result.confidence());
        }

        // 6. 范围不明确时只追问；该问题不是知识结论，不要求来源。
        if (result.replyType() == AiReplyType.CLARIFY
                && result.citations() != null && result.citations().isEmpty()) {
            if (result.answerText() == null || result.answerText().isBlank()) {
                return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, result.confidence());
            }
            return new Verdict(AiReplyType.CLARIFY, result.answerText(), List.of(),
                    result.confidence(), null, true);
        }

        // 7. 通用能力回答(冷启动修订):无引用,置信度达标即放行
        if (result.generalAnswer()) {
            if (result.citations() != null && !result.citations().isEmpty()) {
                return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, result.confidence());
            }
            BigDecimal generalConfidence = result.confidence() == null
                    ? RagResult.ZERO_CONFIDENCE : result.confidence();
            if (generalConfidence.compareTo(properties.getMinConfidence()) < 0) {
                return Verdict.refuse(AiRefusalReason.LOW_CONFIDENCE, generalConfidence);
            }
            String generalText = result.answerText();
            if (generalText == null || generalText.isBlank()) {
                return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, generalConfidence);
            }
            // 通用回答无知识库依据,始终建议转人工入口可见(PRD 8.1)
            return new Verdict(AiReplyType.ANSWER, generalText, List.of(),
                    generalConfidence, null, true);
        }

        // 8. 引用存在性与发布状态(AI-008)。任何一条失效即整体拒答,不做部分保留。
        List<KnowledgeCitationDto> citations = result.citations();
        if (citations == null || citations.isEmpty()) {
            return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, result.confidence());
        }
        try {
            for (KnowledgeCitationDto citation : citations) {
                if (citation == null
                        || !citationValidator.test(citation.articleId(), citation.versionId())) {
                    return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, result.confidence());
                }
            }
        } catch (RuntimeException databaseUnavailable) {
            return Verdict.refuse(AiRefusalReason.MODEL_UNAVAILABLE, RagResult.ZERO_CONFIDENCE);
        }

        // 9. 置信度不足。
        BigDecimal confidence = result.confidence() == null
                ? RagResult.ZERO_CONFIDENCE : result.confidence();
        if (confidence.compareTo(properties.getMinConfidence()) < 0) {
            return Verdict.refuse(AiRefusalReason.LOW_CONFIDENCE, confidence);
        }

        String answerText = result.answerText();
        if (answerText == null || answerText.isBlank()) {
            return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, confidence);
        }

        AiReplyType replyType = result.replyType();
        // 可答但置信度偏低时仍建议转人工,入口始终可见(PRD 8.1、AI-001)
        boolean suggestTransfer =
                confidence.compareTo(properties.getSuggestTransferBelowConfidence()) < 0;
        return new Verdict(replyType, answerText, citations, confidence, null, suggestTransfer);
    }
}
