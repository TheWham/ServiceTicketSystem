package com.itticket.consultation.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** OpenAPI 05 Reason。用于关闭咨询与恢复咨询。 */
public record ReasonRequest(
        @NotBlank @Size(min = 1, max = 2000) String reason) {
}
