package com.itticket.consultation.adapter;

import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.AiReplyType;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

class GuardedRagBudgetTest {
    @Test
    void retrySharesTheOverallRequestDeadline() {
        ConsultationProperties config = new ConsultationProperties();
        config.getAi().setRequestTimeoutMs(400);
        config.getAi().setMaxAttempts(2);
        AtomicInteger attempts = new AtomicInteger();
        RagAdapter adapter = (query, request) -> {
            int attempt = attempts.incrementAndGet();
            try { Thread.sleep(attempt == 1 ? 250 : 300); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            return attempt == 1 ? RagResult.degraded(RagStatus.TIMEOUT, "TIMEOUT", 250)
                    : new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY, "请补充设备信息", List.of(),
                            BigDecimal.ONE, false, "test", List.of(), 300, null);
        };
        GuardedRagClient client = new GuardedRagClient(adapter, config);
        try {
            assertThat(client.answer(query(), "deadline-test").status()).isEqualTo(RagStatus.TIMEOUT);
            assertThat(attempts).hasValue(2);
        } finally { client.shutdown(); }
    }

    @Test
    void missingConfigurationDoesNotRetry() {
        AtomicInteger attempts = new AtomicInteger();
        GuardedRagClient client = new GuardedRagClient((query, request) -> {
            attempts.incrementAndGet();
            return RagResult.degraded(RagStatus.UNAVAILABLE, "NOT_CONFIGURED", 0);
        }, new ConsultationProperties());
        try {
            assertThat(client.answer(query(), "config-test").errorClass()).isEqualTo("NOT_CONFIGURED");
            assertThat(attempts).hasValue(1);
        } finally { client.shutdown(); }
    }
    private RagQuery query() { return new RagQuery("S1", "VPN 无法连接", List.of(), null, null, 3); }
}
