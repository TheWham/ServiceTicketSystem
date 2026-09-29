package com.itticket.consultation.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

/**
 * AI-003 KnowledgeCitation。
 * 每个关键结论至少一条引用(AI-001);引用必须指向仍为 PUBLISHED 的当前版本(AI-008)。
 */
public record KnowledgeCitationDto(
        @NotBlank @Size(max = 64) String articleId,
        @NotBlank @Size(max = 64) String versionId,
        @NotBlank @Size(max = 200) String title,
        @NotNull @DecimalMin("0.0") @DecimalMax("1.0") BigDecimal score,
        @NotBlank @Size(max = 1000) String snippet) {
}
