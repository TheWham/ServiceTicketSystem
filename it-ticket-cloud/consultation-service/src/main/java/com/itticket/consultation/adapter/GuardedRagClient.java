package com.itticket.consultation.adapter;

import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.AiReplyType;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.Semaphore;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * RAG 依赖的隔离壳(RD-003、RD-007、RD-013):上游只依赖本类,不直接依赖 {@link RagAdapter}。
 *
 * <p>四层防御,顺序固定:
 * <ol>
 *   <li><b>断路器</b>(RD-007):{@link SimpleCircuitBreaker} 连续 5 次失败打开、30 秒后半开、
 *       连续 3 次成功关闭(默认值可配)。打开期间<b>不调用适配器</b>,直接返回
 *       {@link RagStatus#UNAVAILABLE};</li>
 *   <li><b>并发上限</b>(RD-007「各自设置最大并发和队列长度;队列满时立即返回对应降级结果,
 *       不等待无限排队」):{@code Semaphore(ai.maxConcurrency)} 用 {@code tryAcquire()} 非阻塞获取,
 *       拿不到立即降级;执行线程池为固定 {@code maxConcurrency} 线程 + 等长有界队列 + AbortPolicy,
 *       与咨询主链路的 Web 线程完全隔离,外部调用不占用主事务连接(RD-013);</li>
 *   <li><b>超时</b>(RD-003「AI/RAG 完整 15 秒」):{@code Future.get(ai.requestTimeoutMs, MILLISECONDS)},
 *       超时即 {@code cancel(true)} 中断任务并返回 {@link RagStatus#TIMEOUT};</li>
 *   <li><b>有界重试</b>(RD-003「同一请求最多 1 次重试」):最多 {@code ai.maxAttempts} 次尝试
 *       (默认 2 = 原始 1 次 + 重试 1 次),且<b>只对 TIMEOUT / UNAVAILABLE 重试</b>;
 *       {@link RagStatus#INVALID_RESPONSE} 属于业务性拒绝,绝不重试。</li>
 * </ol>
 *
 * <p>输出校验(AI-008「模型输出必须先通过 JSON Schema、引用存在性校验再返回客户端」):
 * ANSWER 必须有非空 answerText，知识回答必须有引用，通用办公 IT 建议可无引用；置信度与引用分数必须落在 [0,1],
 * 任一不满足即降级为 {@code INVALID_RESPONSE},不把非法输出透给客户端。
 * 引用是否仍为 PUBLISHED 当前版本由上游用
 * {@code KnowledgeQueryService#isPublishedCurrentVersion} 复核(本地适配器检索时已保证同一口径)。
 *
 * <p><b>本类永不抛异常</b>:任何异常都被归类为显式降级结果(RD-013「降级结果必须是可判定的有限集合」)。
 * 上游据此返回 {@code AI_UNAVAILABLE} 或结构化拒答,并保留转人工与直接提单入口(RD-006、AI-006)。
 *
 * <p>日志(RD-013 可观测性):记录依赖名、断路器状态、错误分类、是否 fallback、尝试次数、
 * requestId、sessionId 与耗时;<b>不记录问题正文、知识正文、提示词与令牌</b>(AI-008、RD-013)。
 *
 * <p>说明:RD-003 的「首段 5 秒」({@code ai.firstTokenTimeoutMs})只适用于 AI-007 的 SSE 流式链路,
 * 本类是非流式同步调用,因此只施加完整回答超时。
 */
@Slf4j
@Component
public class GuardedRagClient {

    /** 依赖名,降级日志与监控维度(RD-010)。 */
    private static final String DEPENDENCY = "rag";

    /** AX-007 错误分类常量。只允许出现分类值,不得拼入异常消息、正文或堆栈(AI-006)。 */
    private static final String ERROR_TIMEOUT = "TIMEOUT";
    private static final String ERROR_CIRCUIT_OPEN = "CIRCUIT_OPEN";
    private static final String ERROR_CONCURRENCY_LIMIT = "CONCURRENCY_LIMIT";
    private static final String ERROR_QUEUE_FULL = "QUEUE_FULL";
    private static final String ERROR_INTERRUPTED = "INTERRUPTED";
    private static final String ERROR_GUARD_FAILURE = "GUARD_FAILURE";
    private static final String ERROR_NULL_QUERY = "NULL_QUERY";
    private static final String ERROR_NULL_RESULT = "NULL_RESULT";
    private static final String ERROR_MISSING_CITATION = "MISSING_CITATION";
    private static final String ERROR_CITATION_INVALID = "CITATION_INVALID";
    private static final String ERROR_CONFIDENCE_RANGE = "CONFIDENCE_OUT_OF_RANGE";
    private static final String ERROR_UNKNOWN = "UNKNOWN";

    private static final AtomicInteger THREAD_SEQ = new AtomicInteger();

    private final RagAdapter adapter;
    private final ConsultationProperties properties;
    private final Semaphore permits;
    private final ThreadPoolExecutor executor;
    private final SimpleCircuitBreaker circuitBreaker;

    public GuardedRagClient(RagAdapter adapter, ConsultationProperties properties) {
        this.adapter = adapter;
        this.properties = properties;
        ConsultationProperties.Ai ai = properties.getAi();
        int concurrency = Math.max(1, ai.getMaxConcurrency());
        this.permits = new Semaphore(concurrency);
        ThreadFactory threadFactory = runnable -> {
            Thread thread = new Thread(runnable, "rag-call-" + THREAD_SEQ.incrementAndGet());
            // 守护线程:RAG 不是主链路,不应阻止应用退出(RD-013)
            thread.setDaemon(true);
            return thread;
        };
        // 有界队列 + AbortPolicy:队列满立即抛 RejectedExecutionException 转降级,不无限排队(RD-007)
        this.executor = new ThreadPoolExecutor(concurrency, concurrency, 0L, TimeUnit.MILLISECONDS,
                new ArrayBlockingQueue<>(concurrency), threadFactory, new ThreadPoolExecutor.AbortPolicy());
        this.circuitBreaker = new SimpleCircuitBreaker(ai.getCircuitFailureThreshold(),
                ai.getCircuitOpenMillis(), ai.getCircuitHalfOpenSuccessThreshold());
    }

    /**
     * 受保护地调用 RAG 适配器。
     *
     * @param query     检索入参,允许为 null(按 INVALID_RESPONSE 降级)
     * @param requestId 请求追踪 ID(RD-010)
     * @return 永不为 null,永不抛异常;{@code status != SUCCESS} 即为降级结果
     */
    public RagResult answer(RagQuery query, String requestId) {
        long startNanos = System.nanoTime();
        String sessionId = query == null ? null : query.sessionId();
        try {
            if (query == null) {
                RagResult invalid = RagResult.degraded(
                        RagStatus.INVALID_RESPONSE, ERROR_NULL_QUERY, elapsedMs(startNanos));
                logDegraded(invalid, requestId, sessionId, 0);
                return invalid;
            }

            int maxAttempts = Math.max(1, properties.getAi().getMaxAttempts());
            RagResult last = null;
            for (int attempt = 1; attempt <= maxAttempts; attempt++) {
                if (!circuitBreaker.allowRequest()) {
                    // 断路器打开:不调用依赖,也不再重试(重试只会继续被拒)
                    last = RagResult.degraded(
                            RagStatus.UNAVAILABLE, ERROR_CIRCUIT_OPEN, elapsedMs(startNanos));
                    logDegraded(last, requestId, sessionId, attempt);
                    break;
                }

                long remainingMs = timeoutMillis() - elapsedMs(startNanos);
                if (remainingMs <= 0) {
                    last = RagResult.degraded(RagStatus.TIMEOUT, ERROR_TIMEOUT, elapsedMs(startNanos));
                    break;
                }
                last = attemptOnce(query, requestId, remainingMs);
                if (last.status() == RagStatus.SUCCESS) {
                    circuitBreaker.recordSuccess();
                    log.debug("[rag] 调用成功 dependency={} circuit={} replyType={} citations={} "
                                    + "attempt={} requestId={} sessionId={} costMs={}",
                            DEPENDENCY, circuitBreaker.state(), last.replyType(),
                            sizeOf(last.citations()), attempt, requestId, sessionId,
                            elapsedMs(startNanos));
                    return last.withLatency(elapsedMs(startNanos));
                }

                circuitBreaker.recordFailure();
                logDegraded(last, requestId, sessionId, attempt);
                if (!retryable(last)) {
                    // RD-003:不得对业务拒绝重试
                    break;
                }
            }
            return last == null
                    ? RagResult.degraded(RagStatus.UNAVAILABLE, ERROR_UNKNOWN, elapsedMs(startNanos))
                    : last.withLatency(elapsedMs(startNanos));
        } catch (Throwable t) {
            // RD-013:主链路不可阻断,任何未预期故障都收敛为降级结果。异常详情只进服务端日志(AI-006)
            log.error("[rag] 隔离壳内部故障 dependency={} requestId={} sessionId={}",
                    DEPENDENCY, requestId, sessionId, t);
            return RagResult.degraded(RagStatus.UNAVAILABLE, ERROR_GUARD_FAILURE, elapsedMs(startNanos));
        }
    }

    /** 当前断路器状态,供健康检查与监控上报使用(RD-010)。 */
    public SimpleCircuitBreaker.State circuitState() {
        return circuitBreaker.state();
    }

    @PreDestroy
    public void shutdown() {
        executor.shutdownNow();
    }

    /** 单次尝试:并发许可 → 线程池执行 → 限时等待 → 输出校验。 */
    private RagResult attemptOnce(RagQuery query, String requestId, long remainingMs) {
        long attemptStart = System.nanoTime();
        if (!permits.tryAcquire()) {
            // RD-007:并发已满立即降级,不阻塞排队
            return RagResult.degraded(
                    RagStatus.UNAVAILABLE, ERROR_CONCURRENCY_LIMIT, elapsedMs(attemptStart));
        }
        // 显式声明 Callable,避免 submit(Runnable) / submit(Callable) 的重载歧义
        Callable<RagResult> task = () -> adapter.answer(query, requestId);
        Future<RagResult> future = null;
        try {
            future = executor.submit(task);
            RagResult result = future.get(remainingMs, TimeUnit.MILLISECONDS);
            return validate(result, elapsedMs(attemptStart));
        } catch (TimeoutException e) {
            // cancel(true) 只发中断信号:JDBC 查询未必立即响应中断,
            // 因此许可在 finally 释放后,残留任务仍占着线程池;后续请求最多被有界队列挡住并立即降级,
            // 不会出现无限排队(RD-007)。
            future.cancel(true);
            return RagResult.degraded(RagStatus.TIMEOUT, ERROR_TIMEOUT, elapsedMs(attemptStart));
        } catch (RejectedExecutionException e) {
            return RagResult.degraded(RagStatus.UNAVAILABLE, ERROR_QUEUE_FULL, elapsedMs(attemptStart));
        } catch (ExecutionException e) {
            return RagResult.degraded(
                    RagStatus.UNAVAILABLE, classify(e.getCause()), elapsedMs(attemptStart));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            if (future != null) {
                future.cancel(true);
            }
            return RagResult.degraded(RagStatus.UNAVAILABLE, ERROR_INTERRUPTED, elapsedMs(attemptStart));
        } finally {
            permits.release();
        }
    }

    /**
     * 输出校验(AI-008、AI-004.3)。不合法一律降级为 {@link RagStatus#INVALID_RESPONSE},
     * 该状态不参与重试(RD-003)。
     *
     * <p>2026-09-29 冷启动放宽策略修订:{@code generalAnswer=true} 的 ANSWER
     * 允许无引用(回答来自模型通用能力而非知识库命中),其余 ANSWER 仍必须有引用。
     */
    private static RagResult validate(RagResult result, long latencyMs) {
        if (result == null || result.status() == null) {
            return RagResult.degraded(RagStatus.INVALID_RESPONSE, ERROR_NULL_RESULT, latencyMs);
        }
        if (result.status() != RagStatus.SUCCESS) {
            return result;
        }
        BigDecimal confidence = result.confidence();
        if (confidence == null || confidence.signum() < 0 || confidence.compareTo(BigDecimal.ONE) > 0) {
            return RagResult.degraded(RagStatus.INVALID_RESPONSE, ERROR_CONFIDENCE_RANGE, latencyMs);
        }
        List<KnowledgeCitationDto> citations = result.citations();
        // AI-004.3:ANSWER 必须有 answerText 且 citations 至少 1 条;
        // 例外:通用能力回答(generalAnswer=true)不携带引用(冷启动放宽策略)
        if (result.replyType() == AiReplyType.ANSWER && !result.generalAnswer()
                && (citations == null || citations.isEmpty() || isBlank(result.answerText()))) {
            return RagResult.degraded(RagStatus.INVALID_RESPONSE, ERROR_MISSING_CITATION, latencyMs);
        }
        if (result.replyType() == AiReplyType.ANSWER && result.generalAnswer()
                && isBlank(result.answerText())) {
            return RagResult.degraded(RagStatus.INVALID_RESPONSE, ERROR_MISSING_CITATION, latencyMs);
        }
        if (citations != null) {
            for (KnowledgeCitationDto citation : citations) {
                if (!isValidCitation(citation)) {
                    return RagResult.degraded(RagStatus.INVALID_RESPONSE, ERROR_CITATION_INVALID, latencyMs);
                }
            }
        }
        return result;
    }

    private static boolean isValidCitation(KnowledgeCitationDto citation) {
        if (citation == null
                || isBlank(citation.articleId())
                || isBlank(citation.versionId())
                || isBlank(citation.title())
                || isBlank(citation.snippet())) {
            return false;
        }
        BigDecimal score = citation.score();
        return score != null && score.signum() >= 0 && score.compareTo(BigDecimal.ONE) <= 0;
    }

    /** RD-003:只对确认可安全重试的瞬时故障重试。 */
    private static boolean retryable(RagResult result) {
        if (result.errorClass() != null && List.of("NOT_CONFIGURED", "RAG_NOT_CONFIGURED", "RAG_AUTH_MISSING", "RAG_AUTH_FAILED",
                "AUTH_FAILED", "PERMANENT", "RAG_BUSINESS_FAILURE", "RAG_INTERRUPTED").contains(result.errorClass())) return false;
        return result.status() == RagStatus.TIMEOUT || result.status() == RagStatus.UNAVAILABLE;
    }

    /** 错误分类只取异常类型简名,不带消息与堆栈(AI-006 错误不得包含堆栈)。 */
    private static String classify(Throwable cause) {
        return cause == null ? ERROR_UNKNOWN : cause.getClass().getSimpleName();
    }

    private void logDegraded(RagResult result, String requestId, String sessionId, int attempt) {
        log.warn("[rag] 依赖降级 dependency={} circuit={} status={} errorClass={} fallback={} "
                        + "attempt={} requestId={} sessionId={} costMs={}",
                DEPENDENCY, circuitBreaker.state(), result.status(), result.errorClass(), true,
                attempt, requestId, sessionId, result.latencyMs());
    }

    private long timeoutMillis() {
        return Math.max(1L, properties.getAi().getRequestTimeoutMs());
    }

    private static int sizeOf(List<?> list) {
        return list == null ? 0 : list.size();
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static long elapsedMs(long startNanos) {
        return (System.nanoTime() - startNanos) / 1_000_000L;
    }
}
