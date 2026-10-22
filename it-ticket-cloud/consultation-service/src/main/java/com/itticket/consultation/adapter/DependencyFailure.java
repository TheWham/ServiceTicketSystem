package com.itticket.consultation.adapter;

import java.util.List;

/** Finite classification; no provider response, prompt or credentials in the exception. */
public final class DependencyFailure extends RuntimeException {
    private final RagStatus status;
    private final String errorClass;
    private final boolean retryable;
    /** 下游 4xx 时响应体里的业务原因（如「分类不存在」），供转成用户可读的报错反馈；无则为 null。 */
    private final String detail;
    public DependencyFailure(RagStatus status, String errorClass, boolean retryable) {
        this(status, errorClass, retryable, null);
    }
    public DependencyFailure(RagStatus status, String errorClass, boolean retryable, String detail) {
        super(errorClass);
        this.status = status; this.errorClass = errorClass; this.retryable = retryable; this.detail = detail;
    }
    public String detail() { return detail; }
    public RagResult result(List<String> retrievedVersionIds) {
        return RagResult.failure(status, errorClass, retryable, retrievedVersionIds);
    }
    public static DependencyFailure invalid() {
        return new DependencyFailure(RagStatus.INVALID_RESPONSE, "INVALID_RESPONSE", false);
    }
}
