package com.itticket.consultation.api;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

import java.util.List;

/**
 * 统一响应结构(PRD 21.1 / OpenAPI 05 Envelope)。
 *
 * <p>{@code errors} 只在字段级校验失败时出现;{@code fallback} 只在 AI 依赖降级时出现(AI-006)。
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@JsonPropertyOrder({"code", "message", "request_id", "data", "errors", "fallback"})
public record ApiEnvelope<T>(
        String code,
        String message,
        @JsonProperty("request_id") String requestId,
        T data,
        List<FieldIssue> errors,
        String fallback) {

    public static <T> ApiEnvelope<T> ok(T data, String requestId) {
        return new ApiEnvelope<>(ApiCode.SUCCESS.name(), ApiCode.SUCCESS.getDefaultMessage(),
                requestId, data, null, null);
    }

    public static <T> ApiEnvelope<T> error(ApiCode code, String message, String requestId,
                                           List<FieldIssue> errors, String fallback) {
        return new ApiEnvelope<>(code.name(), message, requestId, null, errors, fallback);
    }
}
