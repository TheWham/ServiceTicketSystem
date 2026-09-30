package com.itticket.consultation.adapter;

import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.adapter.generation.GenerationResult;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.adapter.retrieval.RetrievalPolicy;
import com.itticket.consultation.adapter.retrieval.RetrievalResult;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.service.KnowledgeQueryService;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class GuardedRagDeadlineTest {
    @Test
    void authenticationFailureIsNeverRetried() {
        AtomicInteger calls = new AtomicInteger();
        GuardedRagClient client = new GuardedRagClient((query, context) -> {
            calls.incrementAndGet();
            return RagResult.degraded(RagStatus.UNAVAILABLE, "AUTH_FAILED", 0);
        }, new ConsultationProperties());
        try {
            assertThat(client.answer(query(), "req").status()).isEqualTo(RagStatus.UNAVAILABLE);
            assertThat(calls).hasValue(1);
        } finally { client.shutdown(); }
    }

    @Test
    void retriesShareOneOverallDeadline() {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setRequestTimeoutMs(1000);
        java.util.List<Long> deadlines = new java.util.concurrent.CopyOnWriteArrayList<>();
        java.util.List<Long> budgets = new java.util.concurrent.CopyOnWriteArrayList<>();
        GuardedRagClient client = new GuardedRagClient((query, context) -> {
            deadlines.add(context.deadlineNanos());
            budgets.add(context.remainingMillis());
            try { Thread.sleep(60); }
            catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
            return RagResult.degraded(RagStatus.UNAVAILABLE, "UNAVAILABLE", 0);
        }, properties);
        try {
            client.answer(query(), "req");
            assertThat(deadlines).hasSize(2);
            assertThat(deadlines.get(1)).isEqualTo(deadlines.get(0));
            assertThat(budgets.get(1)).isLessThan(budgets.get(0) - 30);
        } finally { client.shutdown(); }
    }

    @Test
    void hardDeadlinePreservesVersionsAlreadyRetrievedWithoutWaitingForCancelledWorker() {
        var properties = new ConsultationProperties();
        properties.getAi().setRequestTimeoutMs(500);
        var knowledge = mock(KnowledgeQueryService.class);
        when(knowledge.isPublishedCurrentVersion("A1", "V1")).thenReturn(true);
        var material = new RetrievedKnowledge("C1", "A1", "V1", "排障", "检查输入设备。",
                "检查输入设备。", "C_NET", BigDecimal.ONE, "V1");
        var started = new CountDownLatch(1);
        var release = new CountDownLatch(1);
        var adapter = new ComposedRagAdapter((query, context) -> OfficeDomain.OFFICE_IT,
                (query, context) -> new RetrievalResult(OfficeDomain.OFFICE_IT, true, null,
                        List.of(material), BigDecimal.ONE), new RetrievalPolicy(knowledge),
                (query, input, context) -> {
                    started.countDown();
                    boolean released = false;
                    while (!released) {
                        try {
                            release.await();
                            released = true;
                        } catch (InterruptedException ignored) {
                            // 模拟取消后仍未返回的外部依赖；测试 finally 明确释放工作线程。
                        }
                    }
                    return new GenerationResult(AiReplyType.ANSWER, "检查输入设备。", List.of("V1"),
                            BigDecimal.ONE, null, "test");
                });
        var client = new GuardedRagClient(adapter, properties);
        try {
            long began = System.nanoTime();
            RagResult result = client.answer(query(), "hard-deadline");
            assertThat(result.status()).isEqualTo(RagStatus.TIMEOUT);
            assertThat(started.getCount()).isZero();
            assertThat(result.retrievedVersionIds()).containsExactly("V1");
            assertThat(result.citations()).isEmpty();
            assertThat(release.getCount()).isEqualTo(1);
            assertThat((System.nanoTime() - began) / 1_000_000).isLessThan(3000);
        } finally {
            release.countDown();
            client.shutdown();
        }
    }

    private RagQuery query() { return new RagQuery("S", "打印机连接", null, null, 5, new RagCaller("U_EMP01", "EMPLOYEE")); }
}
