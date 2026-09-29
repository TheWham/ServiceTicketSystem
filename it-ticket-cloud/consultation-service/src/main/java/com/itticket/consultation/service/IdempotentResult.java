package com.itticket.consultation.service;

/**
 * 幂等执行结果。
 *
 * @param value    业务结果
 * @param replayed true 表示命中已有幂等记录,本次没有执行新的业务动作(RD-002)
 */
public record IdempotentResult<T>(T value, boolean replayed) {
}
