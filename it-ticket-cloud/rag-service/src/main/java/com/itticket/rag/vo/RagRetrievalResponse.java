package com.itticket.rag.vo;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.itticket.rag.enums.AiRefusalReason;
import com.itticket.rag.enums.AiReplyType;
import com.itticket.rag.enums.OfficeDomain;

import java.math.BigDecimal;
import java.util.List;

/**
 * ============================================================================
 * RAG 检索响应 (RagRetrievalResponse)
 * ============================================================================
 *
 * <p>本模块只负责「领域判定 + 检索 + 策略判定」，不生成回答。响应给出：</p>
 * <ul>
 *   <li>items：Top-K 已发布知识切片（articleId / versionId / score / snippet / indexVersion，
 *       MR-004 · specs/10-model-rag-integration.md:70）；</li>
 *   <li>domain：领域判定（OFFICE_IT / OFF_TOPIC / HIGH_RISK / UNCERTAIN），上层据此决定能否生成；</li>
 *   <li>suggestedReplyType：建议的回答类型（ANSWER / CLARIFY / REFUSE），仅供参考；</li>
 *   <li>suggestedRefusalReason：拒答时为结构化拒答原因（OFF_TOPIC / HIGH_RISK_TOPIC / LOW_CONFIDENCE / ...，
 *       值域 AI-003 · specs/02-ai-api-json-schema.md:33）；</li>
 *   <li>reliable：是否达到可靠命中阈值 —— true 时可带引用生成；false 时若 domain=OFFICE_IT 且无命中，
 *       按 AI-001（specs/02-ai-api-json-schema.md:14）允许空引用通用回答，不强制拒答。</li>
 * </ul>
 *
 * <p>publishedOnly 恒为 true：检索强制过滤 status=PUBLISHED，已下线版本不会出现
 * （AC-27 · specs/09-prd-spec-test-traceability.md:93 / IT服务工单系统PRD-Ultimate.md:911）。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record RagRetrievalResponse(
        List<RetrievedChunk> items,
        OfficeDomain domain,
        AiReplyType suggestedReplyType,
        AiRefusalReason suggestedRefusalReason,
        BigDecimal topScore,
        boolean reliable,
        boolean publishedOnly) {
}
