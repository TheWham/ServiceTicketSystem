package com.itticket.rag.dto.ai;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

/**
 * 知识引用 —— 契约 AI-003（specs/02-ai-api-json-schema.md:33）/
 * AI-004.3（:134，citation 字段与约束）。
 *
 * <p>score 为余弦相似度换算后的 [0,1] 区间分值；snippet 上限 1000 字符。
 * 组装时必须通过 AI-008（:96）校验：引用指向的版本仍为 PUBLISHED。</p>
 */
public record KnowledgeCitation(
        @NotBlank String articleId,
        @NotBlank String versionId,
        @NotBlank String title,
        BigDecimal score,
        @NotBlank @Size(max = 1000) String snippet) {
}
