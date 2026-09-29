package com.itticket.consultation.dto;

import com.itticket.consultation.enums.ConsultationSource;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** AI-003 / AI-004.1。additionalProperties=false 由 Jackson 未知字段失败保证。 */
public record CreateConsultationRequest(
        @NotNull ConsultationSource source,
        @Size(min = 1, max = 64) String categoryId) {
}
