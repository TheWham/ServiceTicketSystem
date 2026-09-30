package com.itticket.consultation.adapter;

import java.util.List;

/** Finite classification; no provider response, prompt or credentials in the exception. */
public final class DependencyFailure extends RuntimeException {
    private final RagStatus status;
    private final String errorClass;
    private final boolean retryable;
    public DependencyFailure(RagStatus status, String errorClass, boolean retryable) {
        super(errorClass);
        this.status = status; this.errorClass = errorClass; this.retryable = retryable;
    }
    public RagResult result(List<String> retrievedVersionIds) {
        return RagResult.failure(status, errorClass, retryable, retrievedVersionIds);
    }
    public static DependencyFailure invalid() {
        return new DependencyFailure(RagStatus.INVALID_RESPONSE, "INVALID_RESPONSE", false);
    }
}
