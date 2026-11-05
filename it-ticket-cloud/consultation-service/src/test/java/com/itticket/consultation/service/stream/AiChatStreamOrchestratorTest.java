package com.itticket.consultation.service.stream;

import com.itticket.consultation.adapter.StreamAbortedException;
import com.itticket.consultation.adapter.TokenSink;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.enums.RoleCode;
import com.itticket.consultation.service.CurrentUser;
import com.itticket.consultation.statemachine.Actor;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.BooleanSupplier;

import static org.assertj.core.api.Assertions.assertThat;

class AiChatStreamOrchestratorTest {
    private static final CurrentUser USER = new CurrentUser("U_EMP01", RoleCode.EMPLOYEE, Actor.EMPLOYEE);
    private static final AiChatRequest REQUEST = new AiChatRequest("电脑开机黑屏怎么处理", null);
    private static final long BUDGET_MS = 5_000;

    /** 事件记录器:isOpen 可手动关掉,模拟客户端断连。 */
    private static final class RecordingSink implements AiChatStreamOrchestrator.EventSink {
        final List<String> events = new ArrayList<>();
        volatile boolean open = true;

        @Override public void comment(String text) { synchronized (events) { events.add("comment:" + text); } }
        @Override public void queued(int position) { synchronized (events) { events.add("queued:" + position); } }
        @Override public void token(String text) {
            if (!open) throw new IllegalStateException("emit after close");
            synchronized (events) { events.add("token:" + text); }
        }
        @Override public void completed(AiChatResponse response) {
            synchronized (events) { events.add("final:" + response.answerText()); }
        }
        @Override public void failed(String errorClass, String message) {
            synchronized (events) { events.add("error:" + errorClass); }
        }
        @Override public boolean isOpen() { return open; }
    }

    private static AiChatResponse answer(String text) {
        return new AiChatResponse("S1", AiReplyType.ANSWER, text, List.of(), new BigDecimal("0.8"),
                false, null, "local-rag-1.0", "I1", null);
    }

    private static AiChatStreamOrchestrator orchestrator(AiChatStreamOrchestrator.ChunkedChat engine,
                                                         long firstTokenGuardMs) {
        return new AiChatStreamOrchestrator(engine, BUDGET_MS, firstTokenGuardMs, 15_000);
    }

    private static void await(BooleanSupplier condition, long atMostMillis) {
        long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(atMostMillis);
        while (System.nanoTime() < deadline) {
            if (condition.getAsBoolean()) return;
            try { Thread.sleep(10); } catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }
        }
    }

    // ---------------------------------------------------------------- 会话串行

    @Test
    void queuedRequestsAreSerializedPerSessionInFifoOrder() throws Exception {
        CountDownLatch firstStarted = new CountDownLatch(1);
        CountDownLatch releaseFirst = new CountDownLatch(1);
        List<String> order = new ArrayList<>();
        AtomicInteger first = new AtomicInteger();
        AtomicInteger second = new AtomicInteger();
        AiChatStreamOrchestrator.ChunkedChat engine = (user, sessionId, request, key, sink, deadlineNanos) -> {
            if (key.startsWith("k1")) {
                first.incrementAndGet();
                order.add("start1");
                firstStarted.countDown();
                releaseFirst.await();
            } else {
                second.incrementAndGet();
                order.add("start2");
            }
            return answer(key.replace("k", "答"));
        };
        try (AiChatStreamOrchestrator o = orchestrator(engine, 5_000)) {
            RecordingSink a = new RecordingSink();
            RecordingSink b = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            assertThat(firstStarted.await(2, TimeUnit.SECONDS)).isTrue();
            o.openStream(USER, "S1", REQUEST, "k2", b);
            await(() -> !b.events.isEmpty(), 1_000);
            // 第一个还在跑,第二个只能排队并被告知位置
            assertVisibleEvents(b, "queued:1");
            assertThat(second.get()).isZero();

            releaseFirst.countDown();
            await(() -> !b.events.isEmpty() && b.events.get(b.events.size() - 1).startsWith("final:"), 3_000);
            assertVisibleEvents(a, "token:答1", "final:答1");
            assertVisibleEvents(b, "queued:1", "token:答2", "final:答2");
            assertThat(order).containsExactly("start1", "start2");
        }
    }

    @Test
    void differentSessionsRunConcurrently() throws Exception {
        CountDownLatch firstStarted = new CountDownLatch(1);
        CountDownLatch releaseFirst = new CountDownLatch(1);
        AiChatStreamOrchestrator.ChunkedChat engine = (user, sessionId, request, key, sink, deadlineNanos) -> {
            if (sessionId.equals("S1")) {
                firstStarted.countDown();
                releaseFirst.await();
            }
            return answer(sessionId + "的答案");
        };
        try (AiChatStreamOrchestrator o = orchestrator(engine, 5_000)) {
            RecordingSink a = new RecordingSink();
            RecordingSink b = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            assertThat(firstStarted.await(2, TimeUnit.SECONDS)).isTrue();
            o.openStream(USER, "S2", REQUEST, "k2", b);
            await(() -> b.events.contains("final:S2的答案"), 2_000);
            assertThat(b.events).doesNotContain("queued:1");
            releaseFirst.countDown();
            await(() -> a.events.contains("final:S1的答案"), 2_000);
        }
    }

    @Test
    void waitingInQueueBurnsItsOwnDeadlineBeforeStarting() throws Exception {
        CountDownLatch firstStarted = new CountDownLatch(1);
        CountDownLatch releaseFirst = new CountDownLatch(1);
        AtomicInteger slowEngineRuns = new AtomicInteger();
        AtomicInteger doomedEngineRuns = new AtomicInteger();
        AiChatStreamOrchestrator.ChunkedChat engine = (user, sessionId, request, key, sink, deadlineNanos) -> {
            if (key.equals("k-first")) {
                slowEngineRuns.incrementAndGet();
                firstStarted.countDown();
                releaseFirst.await(10, TimeUnit.SECONDS);
                return answer("第一问");
            }
            doomedEngineRuns.incrementAndGet();
            return answer("不该发生");
        };
        // 第二个请求预算只有 150ms,而第一个会占住通道约 400ms
        try (AiChatStreamOrchestrator o = new AiChatStreamOrchestrator(engine, 150, 5_000, 15_000)) {
            RecordingSink a = new RecordingSink();
            RecordingSink b = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k-first", a);
            assertThat(firstStarted.await(2, TimeUnit.SECONDS)).isTrue();
            o.openStream(USER, "S1", REQUEST, "k-second", b);
            await(() -> b.events.contains("error:TIMEOUT"), 2_000);
            assertThat(doomedEngineRuns.get()).isZero();

            assertThat(b.events.get(0)).isEqualTo("queued:1");
            releaseFirst.countDown();
            await(() -> a.events.contains("final:第一问"), 2_000);
            // 前者结束后,排队中已超预算的请求不会再被误执行
            assertThat(doomedEngineRuns.get()).isZero();
        }
    }

    // ---------------------------------------------------------------- 断连

    @Test
    void closedHandleWhileQueuedNeverRuns() throws Exception {
        CountDownLatch firstStarted = new CountDownLatch(1);
        CountDownLatch releaseFirst = new CountDownLatch(1);
        AtomicInteger cancelledRuns = new AtomicInteger();
        AiChatStreamOrchestrator.ChunkedChat engine = (user, sessionId, request, key, sink, deadlineNanos) -> {
            if (key.equals("k1")) {
                firstStarted.countDown();
                releaseFirst.await();
            } else {
                cancelledRuns.incrementAndGet();
            }
            return answer("x");
        };
        try (AiChatStreamOrchestrator o = orchestrator(engine, 5_000)) {
            RecordingSink a = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            assertThat(firstStarted.await(2, TimeUnit.SECONDS)).isTrue();
            RecordingSink b = new RecordingSink();
            AiChatStreamOrchestrator.SseHandle hb = o.openStream(USER, "S1", REQUEST, "k2", b);
            await(() -> !b.events.isEmpty(), 1_000);
            hb.close();
            releaseFirst.countDown();
            await(() -> a.events.contains("final:x"), 2_000);
            assertThat(cancelledRuns.get()).isZero();
            // 被取消的排队项不堵通道:同会话第三个请求立刻处理
            RecordingSink c = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k3", c);
            await(() -> c.events.contains("final:x"), 2_000);
            assertThat(c.events).doesNotContain("queued:1");
        }
    }

    @Test
    void disconnectedClientAbortsStreamWithoutFinalAndReleasesQueue() throws Exception {
        CountDownLatch tokenEmitted = new CountDownLatch(1);
        CountDownLatch engineSawAbort = new CountDownLatch(1);
        AiChatStreamOrchestrator.ChunkedChat dispatcher = (user, sessionId, request, key, sink, deadlineNanos) -> {
            if (key.equals("k1")) {
                sink.accept("第一");
                tokenEmitted.countDown();
                // 继续流式外发;客户端断开后下一次 accept 应把中止信号带回引擎线程
                for (int i = 0; i < 200; i++) {
                    try {
                        Thread.sleep(20);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                    }
                    try {
                        sink.accept("续字" + i);
                    } catch (StreamAbortedException abort) {
                        engineSawAbort.countDown();
                        throw abort;
                    }
                }
                return answer("不该完成");
            }
            return answer("第二问完成");
        };
        try (AiChatStreamOrchestrator o = new AiChatStreamOrchestrator(dispatcher, BUDGET_MS, 5_000, 15_000)) {
            RecordingSink a = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            assertThat(tokenEmitted.await(2, TimeUnit.SECONDS)).isTrue();
            // 客户端在令牌已流出后断连,同时另一条消息进入排队
            a.open = false;
            RecordingSink b = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k2", b);
            assertThat(engineSawAbort.await(3, TimeUnit.SECONDS))
                    .as("断连后引擎的后续令牌应收到中止信号").isTrue();
            await(() -> b.events.contains("final:第二问完成"), 3_000);
            // 断连的第一问不得产生 final
            assertThat(a.events.stream().noneMatch(e -> e.startsWith("final:")))
                    .as("断连流不得有 final 事件").isTrue();
        }
    }

    // ---------------------------------------------------------------- 首字节哨兵

    @Test
    void firstTokenGuardInterruptsStalledLocalGeneration() throws Exception {
        CountDownLatch interrupted = new CountDownLatch(1);
        CountDownLatch guardArmed = new CountDownLatch(1);
        AiChatStreamOrchestrator.ChunkedChat engine = (user, sessionId, request, key, sink, deadlineNanos) -> {
            sink.armFirstTokenGuard();
            guardArmed.countDown();
            try {
                Thread.sleep(10_000);
                return answer("迟到的完整答案");
            } catch (InterruptedException e) {
                interrupted.countDown();
                Thread.currentThread().interrupt();
                // 真实链路里上游被中断后会得到降级结果,守门人将其终结为拒答——这里模拟该终态
                return new AiChatResponse(sessionId, AiReplyType.REFUSE, null, List.of(),
                        BigDecimal.ZERO, false, com.itticket.consultation.enums.AiRefusalReason.MODEL_UNAVAILABLE,
                        "local-rag-1.0", "I1", null);
            }
        };
        try (AiChatStreamOrchestrator o = new AiChatStreamOrchestrator(engine, BUDGET_MS, 60, 15_000)) {
            RecordingSink a = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            assertThat(interrupted.await(2, TimeUnit.SECONDS))
                    .as("首字节哨兵到期应中断上游线程").isTrue();
            await(() -> a.events.stream().anyMatch(e -> e.startsWith("final:")), 3_000);
            assertThat(a.events.stream().anyMatch(e -> e.startsWith("error:"))).isFalse();
        }
    }

    @Test
    void unemittedResponseIsReplayedAsSingleTokenBeforeFinal() throws Exception {
        AiChatStreamOrchestrator.ChunkedChat engine =
                (user, sessionId, request, key, sink, deadlineNanos) -> answer("整段回答");
        try (AiChatStreamOrchestrator o = orchestrator(engine, 5_000)) {
            RecordingSink a = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            await(() -> a.events.contains("final:整段回答"), 2_000);
            // 幂等重放/agent 整段单发的统一收口:引擎没外发过任何 token,编排器补一次整段单发
            assertVisibleEvents(a, "token:整段回答", "final:整段回答");
        }
    }

    // ---------------------------------------------------------------- 传播

    @Test
    void engineExceptionSurfacesAsErrorEventWithClass() throws Exception {
        AiChatStreamOrchestrator.ChunkedChat engine = (user, sessionId, request, key, sink, deadlineNanos) -> {
            throw new IllegalStateException("booh");
        };
        try (AiChatStreamOrchestrator o = orchestrator(engine, 5_000)) {
            RecordingSink a = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            await(() -> !a.events.isEmpty(), 2_000);
            assertThat(a.events).contains("error:INTERNAL_ERROR");
        }
    }

    // ---------------------------------------------------------------- 统一预算(M1, 2026-11-05 评审)

    @Test
    void secondQueuedCallInheritsEnqueueDeadlineNotRefreshedBudget() throws Exception {
        // 排队等待必须烧入自身预算:引擎收到的 deadline 是受理时定下的那一份,
        // 而不是在轮到自己时刷新的满血预算。
        CountDownLatch firstStarted = new CountDownLatch(1);
        CountDownLatch releaseFirst = new CountDownLatch(1);
        List<Long> remainingsAtStart = new CopyOnWriteArrayList<>();
        AiChatStreamOrchestrator.ChunkedChat engine = (user, sessionId, request, key, sink, deadlineNanos) -> {
            remainingsAtStart.add(deadlineNanos - System.nanoTime());
            if (key.startsWith("k1")) {
                firstStarted.countDown();
                releaseFirst.await(1, TimeUnit.SECONDS);
            }
            return answer(key.replace("k", "答"));
        };
        try (AiChatStreamOrchestrator o = orchestrator(engine, 5_000)) {
            RecordingSink a = new RecordingSink();
            RecordingSink b = new RecordingSink();
            o.openStream(USER, "S1", REQUEST, "k1", a);
            assertThat(firstStarted.await(2, TimeUnit.SECONDS)).isTrue();
            Thread.sleep(120); // 第二问在这段时间窗口内入队
            o.openStream(USER, "S1", REQUEST, "k2", b);
            await(() -> b.events.contains("final:答2") && a.events.contains("final:答1"), 3_000);

            assertThat(remainingsAtStart).hasSize(2);
            long budgetNanos = TimeUnit.MILLISECONDS.toNanos(BUDGET_MS);
            assertThat(remainingsAtStart.get(0))
                    .as("第一问几乎立即开始,剩余预算应接近整份")
                    .isGreaterThan(budgetNanos - TimeUnit.MILLISECONDS.toNanos(500));
            assertThat(remainingsAtStart.get(1))
                    .as("第二问等待超过 100ms,剩余预算应明显小于整份(未被刷新)")
                    .isLessThan(budgetNanos - TimeUnit.MILLISECONDS.toNanos(100));
        }
    }

    // ---------------------------------------------------------------- 关停(Mi3)

    @Test
    void closedOrchestratorFailsNewStreamsInsteadOfHanging() {
        // Mi3(2026-11-05 评审): close 后新流不得静默卡死——提交被拒时以真实 INTERNAL_ERROR 终态。
        AiChatStreamOrchestrator.ChunkedChat engine =
                (user, sessionId, request, key, sink, deadlineNanos) -> answer("不应执行");
        AiChatStreamOrchestrator o = orchestrator(engine, 5_000);
        o.close();
        RecordingSink a = new RecordingSink();

        o.openStream(USER, "S1", REQUEST, "k1", a);

        await(() -> !a.events.isEmpty(), 2_000);
        assertThat(a.events).contains("error:INTERNAL_ERROR");
    }

    private static void assertVisibleEvents(RecordingSink sink, String... expectedPrefixes) {
        // 断言事件序列以期望前缀开头(忽略 keep-alive 注释帧)
        List<String> core;
        synchronized (sink.events) {
            core = sink.events.stream()
                    .filter(e -> !e.startsWith("comment:"))
                    .collect(java.util.stream.Collectors.toList());
        }
        int n = Math.min(core.size(), expectedPrefixes.length);
        for (int i = 0; i < n; i++) {
            assertThat(core.get(i)).as("事件#%d", i).isEqualTo(expectedPrefixes[i]);
        }
    }
}
