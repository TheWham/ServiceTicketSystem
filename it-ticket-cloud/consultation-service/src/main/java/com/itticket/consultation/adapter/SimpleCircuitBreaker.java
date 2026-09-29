package com.itticket.consultation.adapter;

/**
 * 最小断路器(RD-007)。
 *
 * <p>状态语义严格按 RD-007 默认值实现,且可由配置覆盖:
 * <ul>
 *   <li>{@code CLOSED} —— 连续 {@code failureThreshold}(默认 5)次失败后打开;</li>
 *   <li>{@code OPEN} —— 打开期间直接拒绝放行,调用方必须立即返回降级结果,
 *       不得调用依赖、不得排队等待;经过 {@code openMillis}(默认 30000)后转入半开;</li>
 *   <li>{@code HALF_OPEN} —— 放行探测请求;连续 {@code halfOpenSuccessThreshold}(默认 3)次
 *       成功后关闭;期间任意一次失败立即重新打开并重新计时。</li>
 * </ul>
 *
 * <p>项目未引入 resilience4j,故自行实现;RD-007 明确「具体实现可替换但必须保留相同的状态语义和监控指标」,
 * {@link #state()} 即为对外暴露的断路器状态指标(RD-010)。
 *
 * <p>线程安全:全部状态变更与读取都在同一把对象锁内完成,
 * 计数器不会因为 RAG 的多线程并发调用而丢失更新。锁内只做整数运算,不会成为热点。
 *
 * <p>一期简化:半开状态不限制并发探测数量,允许多个请求同时探测——
 * 并发上限已由 {@link GuardedRagClient} 的信号量统一约束,此处不再叠加一层限制。
 */
public class SimpleCircuitBreaker {

    /** 断路器状态,对应 RD-010 的监控指标取值。 */
    public enum State {
        CLOSED,
        OPEN,
        HALF_OPEN
    }

    private final int failureThreshold;
    private final long openMillis;
    private final int halfOpenSuccessThreshold;

    private State state = State.CLOSED;
    private int consecutiveFailures;
    private int halfOpenSuccesses;
    private long openedAtMillis;

    /**
     * @param failureThreshold         连续失败多少次打开,小于 1 时按 1 处理
     * @param openMillis               打开持续多久后允许半开探测,负数按 0 处理
     * @param halfOpenSuccessThreshold 半开态连续成功多少次关闭,小于 1 时按 1 处理
     */
    public SimpleCircuitBreaker(int failureThreshold, long openMillis, int halfOpenSuccessThreshold) {
        this.failureThreshold = Math.max(1, failureThreshold);
        this.openMillis = Math.max(0L, openMillis);
        this.halfOpenSuccessThreshold = Math.max(1, halfOpenSuccessThreshold);
    }

    /**
     * 是否放行本次调用。
     *
     * <p>返回 false 时调用方必须立即返回 {@link RagStatus#UNAVAILABLE} 降级结果,
     * 不得调用适配器,也不得等待(RD-007「打开时快速返回定义好的降级结果」)。
     */
    public synchronized boolean allowRequest() {
        if (state == State.OPEN) {
            if (System.currentTimeMillis() - openedAtMillis >= openMillis) {
                state = State.HALF_OPEN;
                halfOpenSuccesses = 0;
                return true;
            }
            return false;
        }
        return true;
    }

    /** 记录一次成功调用。 */
    public synchronized void recordSuccess() {
        if (state == State.HALF_OPEN) {
            halfOpenSuccesses++;
            if (halfOpenSuccesses >= halfOpenSuccessThreshold) {
                close();
            }
            return;
        }
        consecutiveFailures = 0;
    }

    /**
     * 记录一次失败调用。
     *
     * <p>只有真正的依赖故障(超时、不可用、输出非法)才计入;
     * 业务性拒答(无可靠知识)属于成功调用,不得计入失败(RD-001「业务冲突不盲目重试」)。
     */
    public synchronized void recordFailure() {
        if (state == State.HALF_OPEN) {
            open();
            return;
        }
        if (state == State.CLOSED) {
            consecutiveFailures++;
            if (consecutiveFailures >= failureThreshold) {
                open();
            }
        }
    }

    /** 当前状态,供降级日志与监控上报使用(RD-010、RD-013)。 */
    public synchronized State state() {
        return state;
    }

    private void open() {
        state = State.OPEN;
        openedAtMillis = System.currentTimeMillis();
        consecutiveFailures = 0;
        halfOpenSuccesses = 0;
    }

    private void close() {
        state = State.CLOSED;
        consecutiveFailures = 0;
        halfOpenSuccesses = 0;
    }
}
