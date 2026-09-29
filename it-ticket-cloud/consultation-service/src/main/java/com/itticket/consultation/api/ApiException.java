package com.itticket.consultation.api;

import lombok.Getter;

import java.util.List;

/** 业务异常。由 {@link ApiExceptionHandler} 转为统一错误包络。 */
@Getter
public class ApiException extends RuntimeException {

    private final ApiCode code;
    private final transient List<FieldIssue> errors;
    /** AI-006 的 fallback 提示,仅 AI 领域错误使用。 */
    private final String fallback;

    public ApiException(ApiCode code) {
        this(code, code.getDefaultMessage(), null, null);
    }

    public ApiException(ApiCode code, String message) {
        this(code, message, null, null);
    }

    public ApiException(ApiCode code, String message, List<FieldIssue> errors, String fallback) {
        super(message == null ? code.getDefaultMessage() : message);
        this.code = code;
        this.errors = errors;
        this.fallback = fallback;
    }

    public static ApiException validation(List<FieldIssue> errors) {
        return new ApiException(ApiCode.VALIDATION_ERROR, ApiCode.VALIDATION_ERROR.getDefaultMessage(),
                errors, null);
    }

    /**
     * AX-001:不得向无权主体泄露对象存在性,因此"对象不存在"与"无权访问"统一返回 OBJECT_NOT_FOUND。
     */
    public static ApiException notFound() {
        return new ApiException(ApiCode.OBJECT_NOT_FOUND);
    }
}
