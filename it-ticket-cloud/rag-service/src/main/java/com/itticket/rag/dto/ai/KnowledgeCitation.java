package com.itticket.rag.dto.ai;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

/**
 * 知识引用 —— 契约 AI-003 / AI-004.3（citation）。
 *
 * <p>score 为余弦相似度换算后的 [0,1] 区间分值。</p>
 */
public record KnowledgeCitation(
        @NotBlank String articleId,
        @NotBlank String versionId,
        @NotBlank String title,
        BigDecimal score,
        @NotBlank @Size(max = 1000) String snippet) {
}
