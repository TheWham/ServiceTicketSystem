package com.itticket.consultation.dto;

import jakarta.validation.constraints.Size;

/** AI-003 AiContextRefs。 */
public record AiContextRefs(
        @Size(max = 64) String categoryId,
        @Size(max = 64) String assetId) {
}
