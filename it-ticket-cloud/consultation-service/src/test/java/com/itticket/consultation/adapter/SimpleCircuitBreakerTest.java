package com.itticket.consultation.adapter;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 最小断路器状态语义(RD-007)纯单元测试,对应 F-13 / AC-29。
 *
 * <p>契约来源:docs/specs/04-resilience-degradation.md
 * <ul>
 *   <li>RD-007:默认连续 5 次失败打开、30 秒后半开、连续 3 次成功关闭;
 *       「具体实现可替换但必须保留相同的状态语义和监控指标」;</li>
 *   <li>RD-007:断路器打开时快速返回定义好的降级结果,不调用依赖、不排队等待;</li>
 *   <li>RD-006:RAG 不可用时返回拒答并保留转人工与直接提单入口(由 AiAnswerGuard 承接)。</li>
 * </ul>
 *
 * <p>测试用 openMillis=0 让「打开时长届满」瞬间成立,避免单测里 sleep;
 * 需要断言「打开期间拒绝」时才使用较大的 openMillis。
 */
class SimpleCircuitBreakerTest {

    /** RD-007 默认阈值。 */
    private static final int FAILURE_THRESHOLD = 5;
    private static final int HALF_OPEN_SUCCESS_THRESHOLD = 3;
    private static final long OPEN_MILLIS = 30_000L;

    private static SimpleCircuitBreaker defaults() {
        return new SimpleCircuitBreaker(FAILURE_THRESHOLD, OPEN_MILLIS, HALF_OPEN_SUCCESS_THRESHOLD);
    }

    /** openMillis=0:打开后立即满足半开条件,便于在不 sleep 的前提下驱动状态机。 */
    private static SimpleCircuitBreaker instantHalfOpen() {
        return new SimpleCircuitBreaker(FAILURE_THRESHOLD, 0L, HALF_OPEN_SUCCESS_THRESHOLD);
    }

    private static void fail(SimpleCircuitBreaker breaker, int times) {
        for (int i = 0; i < times; i++) {
            breaker.recordFailure();
        }
    }

    private static void succeed(SimpleCircuitBreaker breaker, int times) {
        for (int i = 0; i < times; i++) {
            breaker.recordSuccess();
        }
    }

    // ------------------------------------------------------------------
    // 一、CLOSED -> OPEN
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-13 初始状态为 CLOSED 且放行调用")
    void f13_starts_closed_and_allows_requests() {
        SimpleCircuitBreaker breaker = defaults();

        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);
        assertThat(breaker.allowRequest()).isTrue();
    }

    @Test
    @DisplayName("F-13 连续失败未达阈值(4/5)时保持 CLOSED 并继续放行")
    void f13_stays_closed_below_failure_threshold() {
        SimpleCircuitBreaker breaker = defaults();

        fail(breaker, FAILURE_THRESHOLD - 1);

        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);
        assertThat(breaker.allowRequest()).isTrue();
    }

    @Test
    @DisplayName("AC-29 连续失败达到阈值(5 次)后打开断路器")
    void ac29_opens_after_consecutive_failures_reach_threshold() {
        SimpleCircuitBreaker breaker = defaults();

        fail(breaker, FAILURE_THRESHOLD);

        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);
    }

    @Test
    @DisplayName("F-13 失败计数是「连续」的:中间一次成功即清零,不会误打开")
    void f13_success_resets_consecutive_failure_counter() {
        SimpleCircuitBreaker breaker = defaults();

        fail(breaker, FAILURE_THRESHOLD - 1);
        breaker.recordSuccess();
        fail(breaker, FAILURE_THRESHOLD - 1);

        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);

        breaker.recordFailure();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);
    }

    // ------------------------------------------------------------------
    // 二、OPEN:快速拒绝(RD-007 不调用依赖、不排队)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-29 打开期间拒绝放行,调用方必须立即返回降级结果")
    void ac29_rejects_requests_while_open() {
        SimpleCircuitBreaker breaker = defaults();

        fail(breaker, FAILURE_THRESHOLD);

        assertThat(breaker.allowRequest()).isFalse();
        assertThat(breaker.allowRequest()).isFalse();
        // 被拒绝不改变状态,仍处于 OPEN
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);
    }

    // ------------------------------------------------------------------
    // 三、OPEN -> HALF_OPEN -> CLOSED
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-29 超过打开时长后放行探测请求并转入 HALF_OPEN")
    void ac29_transitions_to_half_open_after_open_duration() {
        SimpleCircuitBreaker breaker = instantHalfOpen();

        fail(breaker, FAILURE_THRESHOLD);
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);

        assertThat(breaker.allowRequest()).isTrue();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.HALF_OPEN);
    }

    @Test
    @DisplayName("AC-29 半开期间连续成功达到阈值(3 次)后关闭,恢复正常放行")
    void ac29_closes_after_half_open_successes_reach_threshold() {
        SimpleCircuitBreaker breaker = instantHalfOpen();

        fail(breaker, FAILURE_THRESHOLD);
        assertThat(breaker.allowRequest()).isTrue();

        succeed(breaker, HALF_OPEN_SUCCESS_THRESHOLD - 1);
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.HALF_OPEN);

        breaker.recordSuccess();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);
        assertThat(breaker.allowRequest()).isTrue();
    }

    @Test
    @DisplayName("AC-29 半开期间任意一次失败立即重新打开")
    void ac29_reopens_on_any_half_open_failure() {
        SimpleCircuitBreaker breaker = instantHalfOpen();

        fail(breaker, FAILURE_THRESHOLD);
        assertThat(breaker.allowRequest()).isTrue();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.HALF_OPEN);

        // 半开态只需一次失败,不必再累计到 failureThreshold
        breaker.recordFailure();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);
    }

    @Test
    @DisplayName("AC-29 半开失败后成功计数清零:重新半开需要重新连续 3 次成功")
    void ac29_half_open_success_counter_is_reset_after_reopen() {
        SimpleCircuitBreaker breaker = instantHalfOpen();

        fail(breaker, FAILURE_THRESHOLD);
        assertThat(breaker.allowRequest()).isTrue();
        succeed(breaker, HALF_OPEN_SUCCESS_THRESHOLD - 1);
        breaker.recordFailure();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);

        // 再次半开:此前累计的 2 次成功不得沿用
        assertThat(breaker.allowRequest()).isTrue();
        succeed(breaker, HALF_OPEN_SUCCESS_THRESHOLD - 1);
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.HALF_OPEN);

        breaker.recordSuccess();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);
    }

    @Test
    @DisplayName("AC-29 关闭后重新累计失败仍需完整阈值才再次打开(半开残留计数不得沿用)")
    void ac29_failure_counter_is_reset_after_close() {
        SimpleCircuitBreaker breaker = instantHalfOpen();

        fail(breaker, FAILURE_THRESHOLD);
        assertThat(breaker.allowRequest()).isTrue();
        succeed(breaker, HALF_OPEN_SUCCESS_THRESHOLD);
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);

        fail(breaker, FAILURE_THRESHOLD - 1);
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);

        breaker.recordFailure();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);
    }

    // ------------------------------------------------------------------
    // 四、参数下界与完整生命周期
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-13 非法阈值按下界处理:阈值 <1 记为 1,openMillis <0 记为 0")
    void f13_invalid_thresholds_fall_back_to_lower_bounds() {
        SimpleCircuitBreaker breaker = new SimpleCircuitBreaker(0, -1L, 0);

        breaker.recordFailure();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);

        assertThat(breaker.allowRequest()).isTrue();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.HALF_OPEN);

        breaker.recordSuccess();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);
    }

    @Test
    @DisplayName("AC-29 完整生命周期:CLOSED -> OPEN -> HALF_OPEN -> CLOSED 各阶段放行语义一致")
    void ac29_full_lifecycle_allow_request_semantics() {
        SimpleCircuitBreaker breaker = instantHalfOpen();

        // CLOSED:放行
        assertThat(breaker.allowRequest()).isTrue();

        // OPEN:openMillis=0 时首个请求即被提升为半开探测,状态不再是 OPEN
        fail(breaker, FAILURE_THRESHOLD);
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.OPEN);
        assertThat(breaker.allowRequest()).isTrue();
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.HALF_OPEN);

        // HALF_OPEN:探测放行
        assertThat(breaker.allowRequest()).isTrue();

        // CLOSED:探测成功后恢复
        succeed(breaker, HALF_OPEN_SUCCESS_THRESHOLD);
        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);
        assertThat(breaker.allowRequest()).isTrue();
    }

    @Test
    @DisplayName("F-13 CLOSED 态的成功调用不会把状态改成别的取值,监控指标稳定(RD-010)")
    void f13_success_in_closed_state_keeps_state_closed() {
        SimpleCircuitBreaker breaker = defaults();

        succeed(breaker, 10);

        assertThat(breaker.state()).isEqualTo(SimpleCircuitBreaker.State.CLOSED);
        assertThat(breaker.allowRequest()).isTrue();
    }
}
