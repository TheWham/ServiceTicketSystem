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
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class GuardedRagDeadlineTest {

    private static long deadline(long millis) {
        return System.nanoTime() + java.util.concurrent.TimeUnit.MILLISECONDS.toNanos(millis);
    }
    @Test
    void authenticationFailureIsNeverRetried() {
        AtomicInteger calls = new AtomicInteger();
        GuardedRagClient client = new GuardedRagClient((query, context, sink) -> {
            calls.incrementAndGet();
            return RagResult.degraded(RagStatus.UNAVAILABLE, "AUTH_FAILED", 0);
        }, new ConsultationProperties());
        try {
            assertThat(client.answer(query(), "req", TokenSink.discarding(), deadline(60_000)).status()).isEqualTo(RagStatus.UNAVAILABLE);
            assertThat(calls).hasValue(1);
        } finally { client.shutdown(); }
    }

    @Test
    void retriesShareOneOverallDeadline() {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setRequestTimeoutMs(1000);
        java.util.List<Long> deadlines = new java.util.concurrent.CopyOnWriteArrayList<>();
        java.util.List<Long> budgets = new java.util.concurrent.CopyOnWriteArrayList<>();
        GuardedRagClient client = new GuardedRagClient((query, context, sink) -> {
            deadlines.add(context.deadlineNanos());
            budgets.add(context.remainingMillis());
            try { Thread.sleep(60); }
            catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
            return RagResult.degraded(RagStatus.UNAVAILABLE, "UNAVAILABLE", 0);
        }, properties);
        try {
            client.answer(query(), "req", TokenSink.discarding(), deadline(1_000));
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
                "检查输入设备。", "C_NET", BigDecimal.ONE, "V1", null, null, null);
        var started = new CountDownLatch(1);
        var release = new CountDownLatch(1);
        var adapter = new ComposedRagAdapter(
                (query, context) -> com.itticket.consultation.adapter.policy.RequestVerdict.of(
                        OfficeDomain.OFFICE_IT, com.itticket.consultation.adapter.policy.RequestVerdict.NO_TOOL),
                (query, context) -> new RetrievalResult(OfficeDomain.OFFICE_IT, true, null,
                        List.of(material), BigDecimal.ONE), new RetrievalPolicy(knowledge, Set.of("SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES"), new BigDecimal("0.10"), 2),
                (query, input, context, sink) -> {
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
                }, false, null, com.itticket.consultation.adapter.cache.SemanticAnswerCache.disabled());
        var client = new GuardedRagClient(adapter, properties);
        try {
            long began = System.nanoTime();
            RagResult result = client.answer(query(), "hard-deadline", TokenSink.discarding(), deadline(60_000));
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
    @Test
    void expiredUnifiedDeadlineFailsFastWithoutCallingAdapter() {
        // M1(2026-11-05 评审): 调用方给定的统一 deadline 已过 → 快速按真实超时降级,
        // 不再消耗断路器/并发额度,更不发起上游调用。
        AtomicInteger calls = new AtomicInteger();
        GuardedRagClient client = new GuardedRagClient((query, context, sink) -> {
            calls.incrementAndGet();
            return new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "答案", List.of(),
                    java.math.BigDecimal.ONE, null, "test", List.of(), 0, null, false, false);
        }, new ConsultationProperties());
        try {
            RagResult result = client.answer(query(), "expired",
                    TokenSink.discarding(), System.nanoTime() - 1_000_000L);
            assertThat(result.status()).isEqualTo(RagStatus.TIMEOUT);
            assertThat(result.errorClass()).isEqualTo("TIMEOUT");
            assertThat(calls.get()).isZero();
        } finally { client.shutdown(); }
    }

}
