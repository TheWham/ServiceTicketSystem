package com.itticket.consultation.adapter;

import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.AiReplyType;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;

class GuardedRagBudgetTest {
    private static long deadline(long millis) {
        return System.nanoTime() + java.util.concurrent.TimeUnit.MILLISECONDS.toNanos(millis);
    }
    @Test
    void retrySharesTheOverallRequestDeadline() {
        ConsultationProperties config = new ConsultationProperties();
        config.getAi().setRequestTimeoutMs(400);
        config.getAi().setMaxAttempts(2);
        AtomicInteger attempts = new AtomicInteger();
        RagAdapter adapter = (query, request, sink) -> {
            int attempt = attempts.incrementAndGet();
            try { Thread.sleep(attempt == 1 ? 250 : 300); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            return attempt == 1 ? RagResult.degraded(RagStatus.TIMEOUT, "TIMEOUT", 250)
                    : new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY, "请补充设备信息", List.of(),
                            BigDecimal.ONE, null, "test", List.of(), 300, null, false, false);
        };
        GuardedRagClient client = new GuardedRagClient(adapter, config);
        try {
            assertThat(client.answer(query(), "deadline-test", TokenSink.discarding(), deadline(400)).status()).isEqualTo(RagStatus.TIMEOUT);
            assertThat(attempts).hasValue(2);
        } finally { client.shutdown(); }
    }

    @Test
    void missingConfigurationDoesNotRetry() {
        AtomicInteger attempts = new AtomicInteger();
        GuardedRagClient client = new GuardedRagClient((query, request, sink) -> {
            attempts.incrementAndGet();
            return RagResult.degraded(RagStatus.UNAVAILABLE, "NOT_CONFIGURED", 0);
        }, new ConsultationProperties());
        try {
            assertThat(client.answer(query(), "config-test", TokenSink.discarding(), deadline(60_000)).errorClass()).isEqualTo("NOT_CONFIGURED");
            assertThat(attempts).hasValue(1);
        } finally { client.shutdown(); }
    }
    @Test
    void emittedTokensSuppressRetry() {
        ConsultationProperties config = new ConsultationProperties();
        config.getAi().setMaxAttempts(2);
        AtomicInteger attempts = new AtomicInteger();
        List<String> tokens = new CopyOnWriteArrayList<>();
        RagAdapter adapter = (query, ctx, sink) -> {
            attempts.incrementAndGet();
            sink.accept("部分");
            // 重试型失败:但 token 已外发,重试会让客户端看到重复字
            return RagResult.degraded(RagStatus.TIMEOUT, "TIMEOUT", 10);
        };
        GuardedRagClient client = new GuardedRagClient(adapter, config);
        try {
            assertThat(client.answer(query(), "stream-retry", TokenSink.of(tokens::add), deadline(60_000)).status())
                    .isEqualTo(RagStatus.TIMEOUT);
            assertThat(attempts).hasValue(1);
            assertThat(tokens).containsExactly("部分");
        } finally { client.shutdown(); }
    }

    private RagQuery query() { return new RagQuery("S1", "VPN 无法连接", null, null, 3, new RagCaller("U1", "EMPLOYEE")); }
}
