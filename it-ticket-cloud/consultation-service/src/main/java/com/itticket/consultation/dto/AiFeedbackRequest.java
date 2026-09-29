package com.itticket.consultation.dto;

import com.itticket.consultation.enums.AiFeedbackType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** AI-003 / AI-004.4 反馈请求。 */
public record AiFeedbackRequest(
        @NotBlank @Size(max = 64) String interactionId,
        @NotNull AiFeedbackType feedback,
        @Size(max = 2000) String comment) {
}
