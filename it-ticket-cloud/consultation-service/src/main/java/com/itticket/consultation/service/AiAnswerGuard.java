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
 * <p><b>2026-09-29 冷启动放宽策略修订</b>:知识库无命中时不再一律拒答。
 * 适配器标记 {@code generalAnswer=true} 的回答(知识无命中或不足时的办公 IT 通用建议)
 * 允许无引用放行,但置信度必须达标且建议转人工入口保持可见;
 * 语义分类超范围({@code offTopic=true})时按 {@code OFF_TOPIC} 拒答，高风险操作转人工。
 * 只要使用知识引用就严格复核；检索到不相关资料不强制挂载来源。
 *
 * <p>判定优先级(先命中先返回,保证降级原因唯一且可判定 —— RD-013):
 * <ol>
 *   <li>评测未达上线门槛 → POLICY_BLOCKED(PRD 17.3);</li>
 *   <li>高风险主题 → HIGH_RISK_TOPIC(AI-001);</li>
 *   <li>依赖超时/不可用/断路器打开 → MODEL_UNAVAILABLE(RD-006);</li>
 *   <li>模型输出不合 Schema → NO_RELIABLE_KNOWLEDGE，不透传非法输出；</li>
 *   <li>语义高风险判定 → HIGH_RISK_TOPIC；</li>
 *   <li>知识冲突 → CONFLICTING_KNOWLEDGE;</li>
 *   <li>超范围咨询 → OFF_TOPIC(冷启动修订新增);</li>
 *   <li>适配器自判拒答(非超范围) → NO_RELIABLE_KNOWLEDGE;</li>
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
     * @param highRiskHit      用户问题是否命中高风险主题
     * @param citationValidator (articleId, versionId) → 是否仍为 PUBLISHED 的当前版本
     */
    public static Verdict evaluate(RagResult result,
                                   ConsultationProperties.Ai properties,
                                   boolean highRiskHit,
                                   BiPredicate<String, String> citationValidator) {
        // 1. AI 评测未达上线门槛:只关闭综合回答,其余入口不受影响(PRD 17.3、RD-006)
        if (!properties.isAnswerEnabled()) {
            return Verdict.refuse(AiRefusalReason.POLICY_BLOCKED, RagResult.ZERO_CONFIDENCE);
        }
        // 2. 高风险主题优先引导转人工,不调用模型也不展示生成回答(AI-001)
        if (highRiskHit) {
            return Verdict.refuse(AiRefusalReason.HIGH_RISK_TOPIC, RagResult.ZERO_CONFIDENCE);
        }
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
        // 5. 知识冲突
        if (result.highRiskTopic()) {
            return Verdict.refuse(AiRefusalReason.HIGH_RISK_TOPIC, RagResult.ZERO_CONFIDENCE);
        }
        if (result.knowledgeConflict()) {
            return Verdict.refuse(AiRefusalReason.CONFLICTING_KNOWLEDGE, result.confidence());
        }
        // 6. 超范围咨询:只能答复 IT 办公类问题(冷启动修订新增)
        if (result.offTopic()) {
            return Verdict.refuse(AiRefusalReason.OFF_TOPIC, result.confidence());
        }
        // 适配器自身已判定无可靠命中(非超范围)
        if (result.replyType() == AiReplyType.REFUSE) {
            return Verdict.refuse(result.refusalReason() == null
                    ? AiRefusalReason.NO_RELIABLE_KNOWLEDGE : result.refusalReason(), result.confidence());
        }

        // 范围不明确时只追问；该问题不是知识结论，不要求来源。
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
        for (KnowledgeCitationDto citation : citations) {
            if (citation == null
                    || !citationValidator.test(citation.articleId(), citation.versionId())) {
                return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, result.confidence());
            }
        }

        // 9. 置信度不足
        BigDecimal confidence = result.confidence() == null
                ? RagResult.ZERO_CONFIDENCE : result.confidence();
        if (confidence.compareTo(properties.getMinConfidence()) < 0) {
            return Verdict.refuse(AiRefusalReason.LOW_CONFIDENCE, confidence);
        }

        String answerText = result.answerText();
        if (answerText == null || answerText.isBlank()) {
            return Verdict.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, confidence);
        }

        AiReplyType replyType = result.replyType() == null ? AiReplyType.ANSWER : result.replyType();
        // 可答但置信度偏低时仍建议转人工,入口始终可见(PRD 8.1、AI-001)
        boolean suggestTransfer =
                confidence.compareTo(properties.getSuggestTransferBelowConfidence()) < 0;
        return new Verdict(replyType, answerText, citations, confidence, null, suggestTransfer);
    }

    /** AI-001 高风险主题判定:大小写不敏感的关键词包含匹配。 */
    public static boolean matchesHighRisk(String message, List<String> keywords) {
        if (message == null || keywords == null || keywords.isEmpty()) {
            return false;
        }
        String normalized = message.toLowerCase(java.util.Locale.ROOT);
        for (String keyword : keywords) {
            if (keyword != null && !keyword.isBlank()
                    && normalized.contains(keyword.toLowerCase(java.util.Locale.ROOT))) {
                return true;
            }
        }
        return false;
    }
}
