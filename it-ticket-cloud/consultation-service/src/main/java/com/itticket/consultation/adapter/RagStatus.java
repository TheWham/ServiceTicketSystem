package com.itticket.consultation.adapter;

/**
 * RAG 适配器统一结果状态(AX-003:适配器统一返回 SUCCESS | RETRYABLE_FAILURE | PERMANENT_FAILURE | UNAVAILABLE)。
 *
 * <p>本适配器按 AX-007 的错误分类收敛为四个值:
 * <ul>
 *   <li>{@link #SUCCESS} —— 调用完成且输出通过校验,可能是 ANSWER 也可能是结构化拒答;</li>
 *   <li>{@link #TIMEOUT} —— 超过 RD-003 的 AI/RAG 完整回答超时,可重试;</li>
 *   <li>{@link #UNAVAILABLE} —— 依赖不可用、并发上限、队列满或断路器打开(RD-006/RD-007),可重试;</li>
 *   <li>{@link #INVALID_RESPONSE} —— 输出不满足 AI-004 Schema 或引用缺失(AI-008),
 *       属于业务性拒绝,<b>不得重试</b>(RD-003)。</li>
 * </ul>
 *
 * <p>任何非 SUCCESS 都必须是显式可判定的降级结果,不允许用空成功掩盖失败(RD-013)。
 */
public enum RagStatus {
    SUCCESS,
    TIMEOUT,
    UNAVAILABLE,
    INVALID_RESPONSE
}
