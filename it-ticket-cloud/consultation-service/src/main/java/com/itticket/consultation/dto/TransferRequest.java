package com.itticket.consultation.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * AI-003 / AI-004.4 转人工请求。
 * 不接受员工指定工程师(AI-API-004),也不接受员工选择优先级。
 */
public record TransferRequest(
        @NotBlank @Size(min = 1, max = 64) String categoryId) {
}
