package com.itticket.consultation.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** AI-003 / AI-004.2。 */
public record AiChatRequest(
        @NotBlank @Size(max = 8000) String message,
        @Valid AiContextRefs contextRefs) {
}
