package com.itticket.rag.vo;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.itticket.rag.enums.AiRefusalReason;

import java.math.BigDecimal;
import java.util.List;

/**
 * ============================================================================
 * RAG 检索响应 (RagRetrievalResponse)
 * ============================================================================
 *
 * <p>本模块只负责「检索 + 策略判定」，不生成回答。响应给出：</p>
 * <ul>
 *   <li>items：Top-K 已发布知识切片（对接方拼装 Prompt 用）；</li>
 *   <li>reliable：是否达到可靠命中阈值 —— false 时对接方应拒答；</li>
 *   <li>suggestedRefusalReason：建议的拒答原因（AI-001 语义），对接方直接透传即可。</li>
 * </ul>
 *
 * <p>publishedOnly 恒为 true：检索强制过滤 status=PUBLISHED，已下线版本不会出现（AC-27）。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record RagRetrievalResponse(
        List<RetrievedChunk> items,
        BigDecimal topSimilarity,
        boolean reliable,
        boolean highRiskBlocked,
        String matchedKeyword,
        AiRefusalReason suggestedRefusalReason,
        boolean publishedOnly) {
}
