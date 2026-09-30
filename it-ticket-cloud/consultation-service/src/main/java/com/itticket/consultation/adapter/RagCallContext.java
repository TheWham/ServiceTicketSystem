package com.itticket.consultation.adapter;
import java.util.concurrent.TimeUnit;
import java.util.Objects;

/** Immutable deadline and request identity, with separate per-request execution audit state. */
public record RagCallContext(String requestId, long deadlineNanos, RagExecutionAudit audit) {
    public RagCallContext {
        Objects.requireNonNull(audit, "audit");
    }

    public long remainingMillis() {
        return Math.max(0, TimeUnit.NANOSECONDS.toMillis(deadlineNanos - System.nanoTime()));
    }
    public long timeoutMillis(long maximum) {
        long remaining = remainingMillis();
        if (remaining == 0 || Thread.currentThread().isInterrupted())
            throw new DependencyFailure(RagStatus.TIMEOUT, "TIMEOUT", false);
        return Math.min(Math.max(1, maximum), remaining);
    }
}
