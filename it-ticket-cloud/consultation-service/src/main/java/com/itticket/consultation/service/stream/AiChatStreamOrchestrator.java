package com.itticket.consultation.service.stream;

import com.itticket.consultation.adapter.StreamAbortedException;
import com.itticket.consultation.adapter.TokenSink;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.service.CurrentUser;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.SmartLifecycle;

import java.util.ArrayDeque;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * AI 流式回答的服务端编排器(T-5)。
 *
 * <p>职责只有三件,全部与「什么时候轮到谁」有关;业务(鉴权/幂等/检索/生成/落库)
 * 全部由注入的 {@link ChunkedChat}(即 AiConsultationService 的流式门面)完成:
 * <ol>
 *   <li><b>会话 FIFO 串行</b>(裁决 m00909):同一会话一次只处理一条消息,
 *       后到消息照常进入流,先收到 queued(position) 排队事件,前一问到达终态后
 *       才开始处理。排队等待计入该请求自身的统一预算,超限时以真实原因
 *       failed(TIMEOUT) 终态,不假装队列空闲;</li>
 *   <li><b>出口协议</b>:comment(keep-alive, 默认 15s 一帧,排队与生成期间都有)/
 *       queued(position)/token(增量答案文本)/final(业务终态,含拒答)/
 *       error(真实 errorClass)。final 语义与旧同步端点一致——到达 final 时
 *       幂等与落库已在引擎内完成;</li>
 *   <li><b>断连与首字节哨兵</b>:客户端断开后,未开始的排队项静默清除,进行中的
 *       流在下一个令牌出口被中止(引擎因此不会半落库);本地生成路径由引擎侧
 *       调用 {@link TokenSink#armFirstTokenGuard()} 布设首字节哨兵,到期未见到
 *       首字节即中断上游,缓存命中与 agent 路径不布哨兵天然豁免(裁决①)。</li>
 * </ol>
 *
 * <p>失败语义遵守红线:不静默回退,不在断连后补发事件,不在编排层吞掉业务异常——
 * 业务异常映射为 error(Existing ApiCode 名) 事件原样透出。
 */
@Slf4j
public class AiChatStreamOrchestrator implements AutoCloseable, SmartLifecycle {

    /** 流式引擎门面:即 AiConsultationService#chatStreamed。 */
    public interface ChunkedChat {
        AiChatResponse run(CurrentUser user, String sessionId, AiChatRequest request,
                           String idempotencyKey, TokenSink sink, long deadlineNanos) throws Exception;
    }

    /** SSE 事件出口。所有回调要求幂等安全;isOpen=false 之后不得再收到任何事件。 */
    public interface EventSink {
        /** 空转帧(SSE 注释行),仅为保活与断连探测。 */
        void comment(String text);

        /** 排队受理:本会话前方还有 position 条未终态消息。 */
        void queued(int position);

        /** 增量答案文本(打字机)。 */
        void token(String text);

        /** 业务终态:与旧同步端点相同的完整应答(含拒答)。 */
        void completed(AiChatResponse response);

        /** 失败终态:errorClass 复用既有错误词表(TIMEOUT/业务 ApiCode 名/INTERNAL_ERROR)。 */
        void failed(String errorClass, String message);

        boolean isOpen();
    }

    /** 客户端侧句柄:断开连接/超时时调用 close() 取消本流。 */
    public interface SseHandle {
        void close();
    }

    private enum CallState { QUEUED, ACTIVE, DONE }

    /** 单条流式请求的全部运行时状态。state 的变更都在所属会话队列锁内。 */
    private static final class StreamCall {
        final CurrentUser user;
        final String sessionId;
        final AiChatRequest request;
        final String idempotencyKey;
        final EventSink out;
        final long deadlineNanos;
        final StreamSink sink;
        CallState state = CallState.QUEUED;
        volatile Thread worker;
        volatile boolean closedByClient;
        Future<?> workerFuture;
        ScheduledFuture<?> queueDeadlineTask;
        ScheduledFuture<?> keepAliveTask;

        StreamCall(CurrentUser user, String sessionId, AiChatRequest request,
                   String idempotencyKey, EventSink out, long deadlineNanos, AiChatStreamOrchestrator owner) {
            this.user = user;
            this.sessionId = sessionId;
            this.request = request;
            this.idempotencyKey = idempotencyKey;
            this.out = out;
            this.deadlineNanos = deadlineNanos;
            this.sink = owner.new StreamSink(this);
        }
    }

    /** 编排器持有的流式出口:断连标记 + 首字节哨兵。 */
    private final class StreamSink extends TokenSink {
        private final StreamCall call;
        private volatile ScheduledFuture<?> guard;

        StreamSink(StreamCall call) {
            super(piece -> call.out.token(piece));
            this.call = call;
        }

        @Override public void accept(String token) {
            if (clientGone()) throw new StreamAbortedException("客户端已断开,本流已收口");
            // 首字节已到达:撤哨兵(包括空串被基类忽略时也不误伤——哨兵只关心真实外发)
            ScheduledFuture<?> g = guard;
            if (g != null) {
                g.cancel(false);
                guard = null;
            }
            super.accept(token);
        }

        @Override public boolean clientGone() {
            return call.closedByClient || !call.out.isOpen();
        }

        @Override public void armFirstTokenGuard() {
            if (guard != null || firstTokenGuardMillis <= 0) return;
            guard = scheduler.schedule(() -> {
                Thread worker = call.worker;
                if (clientGone() || worker == null) return;
                log.warn("[ai-stream] 首字节超时 sessionId={} requestId={},中断上游生成",
                        call.sessionId, call.idempotencyKey);
                worker.interrupt();
            }, firstTokenGuardMillis, TimeUnit.MILLISECONDS);
        }

        private void cancelGuard() {
            ScheduledFuture<?> g = guard;
            if (g != null) g.cancel(false);
        }
    }

    /** 会话队列:active 表示该会话是否有一条消息在处理。 */
    private static final class SessionQueue {
        final ArrayDeque<StreamCall> waiting = new ArrayDeque<>();
        boolean active;
    }

    private final ChunkedChat engine;
    private final long budgetMillis;
    private final long firstTokenGuardMillis;
    private final long keepAliveMillis;
    private final Map<String, SessionQueue> sessions = new ConcurrentHashMap<>();
    private final AtomicLong threadSeq = new AtomicLong();
    private final ExecutorService executor = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "ai-stream-" + threadSeq.incrementAndGet());
        t.setDaemon(true);
        return t;
    });
    private final ScheduledExecutorService scheduler =
            Executors.newScheduledThreadPool(2, r -> {
                Thread t = new Thread(r, "ai-stream-sched-" + threadSeq.incrementAndGet());
                t.setDaemon(true);
                return t;
            });

    public AiChatStreamOrchestrator(ChunkedChat engine, long requestBudgetMillis,
                                    long firstTokenGuardMillis, long keepAliveMillis) {
        this.engine = Objects.requireNonNull(engine, "engine");
        this.budgetMillis = requestBudgetMillis;
        this.firstTokenGuardMillis = firstTokenGuardMillis;
        this.keepAliveMillis = keepAliveMillis;
    }

    // ---------------------------------------------------------------- 对外

    /**
     * 开一条流式回答。事件回调可能来自工作线程与调度线程,实现方需自行保证顺序安全;
     * 本方法返回后 queued 事件可能已经发生,实现在构造时就要可用。
     */
    public SseHandle openStream(CurrentUser user, String sessionId, AiChatRequest request,
                                String idempotencyKey, EventSink out) {
        Objects.requireNonNull(user, "user");
        Objects.requireNonNull(sessionId, "sessionId");
        Objects.requireNonNull(request, "request");
        Objects.requireNonNull(idempotencyKey, "idempotencyKey");
        Objects.requireNonNull(out, "out");

        SessionQueue queue = sessions.computeIfAbsent(sessionId, key -> new SessionQueue());
        StreamCall call = new StreamCall(user, sessionId, request, idempotencyKey, out,
                System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(budgetMillis), this);

        boolean immediate;
        int position = 0;
        synchronized (queue) {
            if (queue.active) {
                queue.waiting.addLast(call);
                position = queue.waiting.size();
                // Mi2(2026-11-05 评审):queued 事件在队列锁内发出,避免“入队后、发事件前”
                // 被并发终态插队而出现位置跳变;EventSink 实现不再回调编排器,无死锁环。
                out.queued(position);
                immediate = false;
            } else {
                queue.active = true;
                call.state = CallState.ACTIVE;
                immediate = true;
            }
        }
        if (immediate) {
            submitWorker(call, queue);
        } else {
            // 裁决 m00909:排队等待计入自身统一预算;到期仍未轮到即以真实原因终态。
            try {
                call.queueDeadlineTask = scheduler.schedule(
                        () -> expireWhileQueued(call, queue), budgetMillis, TimeUnit.MILLISECONDS);
            } catch (RejectedExecutionException rejected) {
                // 调度器已关停:预算到期哨兵不可布设。若工作池同已关停,首条 ACTIVE 流
                // 会经 submitWorker 以 INTERNAL_ERROR 终态并逐条放行队列,不会静默悬挂。
                call.queueDeadlineTask = null;
            }
        }
        if (keepAliveMillis > 0) {
            try {
                call.keepAliveTask = scheduler.scheduleAtFixedRate(() -> keepAlive(call),
                        keepAliveMillis, keepAliveMillis, TimeUnit.MILLISECONDS);
            } catch (RejectedExecutionException rejected) {
                call.keepAliveTask = null; // 已在关停中:保活缺失不影响终态链路。
            }
        }
        return () -> clientClose(call, queue);
    }

    @Override public void close() {
        executor.shutdownNow();
        scheduler.shutdownNow();
    }

    // ---------------------------------------------------------------- 生命周期

    @Override public void start() {
        // 线程池在构造时即就绪;SmartLifecycle 仅为了让容器关闭时停掉守护线程。
    }

    @Override public void stop() {
        close();
    }

    @Override public boolean isRunning() {
        return !executor.isShutdown();
    }

    // ---------------------------------------------------------------- 内部

    private void run(StreamCall call, SessionQueue queue) {
        call.worker = Thread.currentThread();
        RequestContext.set("ai-stream-" + call.idempotencyKey);
        try {
            if (call.state != CallState.ACTIVE) return; // 已被取消/超时收走,通道归属不在本条
            if (call.sink.clientGone()) return;
            if (System.nanoTime() > call.deadlineNanos) {
                call.out.failed("TIMEOUT", "排队等待超出请求预算");
                return;
            }
            AiChatResponse response = engine.run(call.user, call.sessionId,
                    call.request, call.idempotencyKey, call.sink, call.deadlineNanos);
            if (call.sink.clientGone()) return;
            // 幂等重放与 agent 整段场景统一收口:引擎没外发过任何令牌时,这里整段单发一次,
            // 前端打字机一次性收尾,final 随后即达。
            if (!call.sink.emitted() && response != null && response.answerText() != null
                    && !response.answerText().isBlank()) {
                call.sink.accept(response.answerText());
            }
            call.out.completed(response);
        } catch (StreamAbortedException gone) {
            // 客户端断连:静默收尾,不向已断开的出口补发任何事件。
            log.info("[ai-stream] 客户端断连终止 sessionId={} requestId={}",
                    call.sessionId, call.idempotencyKey);
        } catch (ApiException business) {
            call.out.failed(business.getCode() == null ? "BUSINESS_RULE" : business.getCode().name(),
                    business.getMessage());
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            call.out.failed("TIMEOUT", "本次回答被中断");
        } catch (Throwable t) {
            log.warn("[ai-stream] 流式回答处理失败 sessionId={} requestId={}",
                    call.sessionId, call.idempotencyKey, t);
            call.out.failed("INTERNAL_ERROR", "AI 流式回答处理失败");
        } finally {
            call.sink.cancelGuard();
            RequestContext.clear();
            finish(call, queue);
        }
    }

    /** ACTIVE 调用终态:放行下一条排队消息或关闭会话队列。 */
    private void finish(StreamCall call, SessionQueue queue) {
        StreamCall next = null;
        synchronized (queue) {
            if (call.state == CallState.ACTIVE) {
                call.state = CallState.DONE;
                next = queue.waiting.pollFirst();
                if (next != null) {
                    next.state = CallState.ACTIVE;
                } else {
                    queue.active = false;
                    sessions.remove(call.sessionId, queue);
                }
            }
        }
        cancelScheduled(call);
        if (next != null) {
            StreamCall started = next;
            if (started.queueDeadlineTask != null) {
                started.queueDeadlineTask.cancel(false);
                started.queueDeadlineTask = null;
            }
            submitWorker(started, queue);
        }
    }

    /**
     * Mi3(2026-11-05 评审):提交被拒(编排器已 close 或池饱和)时流不得静默卡死——
     * 以真实 INTERNAL_ERROR 终态回执,并用 finish() 释放会话队列,让排队消息继续。
     */
    private void submitWorker(StreamCall call, SessionQueue queue) {
        try {
            call.workerFuture = executor.submit(() -> run(call, queue));
        } catch (RejectedExecutionException rejected) {
            log.warn("[ai-stream] 工作池已拒绝新任务, 流以 INTERNAL_ERROR 终态 idKey={}", call.idempotencyKey);
            call.out.failed("INTERNAL_ERROR", "流式执行器不可用");
            finish(call, queue);
        }
    }

    private void expireWhileQueued(StreamCall call, SessionQueue queue) {
        boolean taken = false;
        synchronized (queue) {
            if (call.state == CallState.QUEUED) {
                queue.waiting.removeFirstOccurrence(call);
                call.state = CallState.DONE;
                taken = true;
            }
        }
        if (taken) {
            cancelScheduled(call);
            call.out.failed("TIMEOUT", "排队等待超出请求预算");
        }
    }

    private void clientClose(StreamCall call, SessionQueue queue) {
        call.closedByClient = true;
        // 排队中的断连:直接清除,不产生事件(出口已不可用)
        boolean removedActive = false;
        synchronized (queue) {
            if (call.state == CallState.QUEUED) {
                queue.waiting.removeFirstOccurrence(call);
                call.state = CallState.DONE;
            } else if (call.state == CallState.ACTIVE) {
                removedActive = true;
            }
        }
        if (removedActive) {
            boolean cancelled = call.workerFuture != null && call.workerFuture.cancel(true);
            // 任务尚未真正开跑(cancel 成功且工作线程未露面):队列归属收回到本条,直接放行下一条。
            if (cancelled && call.worker == null) {
                finish(call, queue);
            }
            // 已开跑:run() 的 finally 会在引擎返回(被中断后)后放行队列。
        } else {
            cancelScheduled(call);
        }
    }

    private void keepAlive(StreamCall call) {
        if (call.closedByClient) return;
        if (call.sink.clientGone()) {
            // 心跳发现断连:立即置标记,正在生成的流会在下一个令牌出口中止。
            call.closedByClient = true;
            return;
        }
        call.out.comment("keep-alive");
    }

    private void cancelScheduled(StreamCall call) {
        if (call.queueDeadlineTask != null) {
            call.queueDeadlineTask.cancel(false);
            call.queueDeadlineTask = null;
        }
        if (call.keepAliveTask != null) {
            call.keepAliveTask.cancel(false);
            call.keepAliveTask = null;
        }
        call.sink.cancelGuard();
    }
}
