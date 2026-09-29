package com.itticket.consultation.adapter;

/**
 * RAG/模型适配器(AX-007:同步且隔离的外部适配器签名)。
 *
 * <p>实现方只允许检索 {@code PUBLISHED} 且为当前版本的知识(AI-001、RD-006「不检索已下线版本」),
 * 不得执行命令、调用业务系统或修改工单(AI-001)。
 *
 * <p>实现方<b>不需要</b>自带超时、重试、并发上限与断路器:这些由 {@link GuardedRagClient} 统一施加
 * (RD-003、RD-007);实现方抛出的异常由 GuardedRagClient 归类为降级结果,主链路不可被阻断(RD-013)。
 */
public interface RagAdapter {

    /**
     * 基于已发布知识生成受约束回答。
     *
     * @param query     检索入参,不为空
     * @param requestId 请求追踪 ID(RD-010),用于日志与读幂等键(AX-007)
     * @return 非空结果;失败语义由 {@link RagStatus} 表达
     */
    RagResult answer(RagQuery query, String requestId);
}
