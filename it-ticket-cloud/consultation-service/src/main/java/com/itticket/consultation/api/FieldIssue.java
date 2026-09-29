package com.itticket.consultation.api;

import com.fasterxml.jackson.annotation.JsonInclude;

/** 字段级错误(PRD 21.1 字段错误结构)。 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record FieldIssue(String field, String reason, String message) {

    public static FieldIssue required(String field, String message) {
        return new FieldIssue(field, "REQUIRED", message);
    }

    public static FieldIssue invalid(String field, String message) {
        return new FieldIssue(field, "INVALID", message);
    }
}
