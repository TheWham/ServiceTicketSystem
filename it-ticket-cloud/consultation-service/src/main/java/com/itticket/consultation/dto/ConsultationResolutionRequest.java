package com.itticket.consultation.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** OpenAPI 05 ConsultationResolution。工程师提交解决结论,结论非空(SM-CONSULT-001)。 */
public record ConsultationResolutionRequest(
        @NotBlank @Size(min = 1, max = 12000) String conclusion) {
}
