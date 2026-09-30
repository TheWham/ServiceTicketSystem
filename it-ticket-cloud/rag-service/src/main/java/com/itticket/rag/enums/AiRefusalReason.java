package com.itticket.rag.enums;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * AI 结构化拒答原因 —— 契约 AI-003（specs/02-ai-api-json-schema.md:33）值域（7 值）。
 *
 * <p>注意：这是拒答原因，不是 HTTP 错误码；HTTP 层 AI 领域失败使用 AI-* 错误码。</p>
 */
public enum AiRefusalReason {
    /** 无可靠命中：检索为空或相似度低于下限 */
    NO_RELIABLE_KNOWLEDGE("NO_RELIABLE_KNOWLEDGE"),
    /** 置信度不足：有命中但相似度低于生成阈值 */
    LOW_CONFIDENCE("LOW_CONFIDENCE"),
    /** 知识冲突：多条知识结论互相矛盾 */
    CONFLICTING_KNOWLEDGE("CONFLICTING_KNOWLEDGE"),
    /** 高风险主题：权限变更/安全事件处置/数据恢复/高风险命令/硬件拆修（AI-001） */
    HIGH_RISK_TOPIC("HIGH_RISK_TOPIC"),
    /** 模型或向量服务不可用（RD-006 降级 · specs/04-resilience-degradation.md:67） */
    MODEL_UNAVAILABLE("MODEL_UNAVAILABLE"),
    /** 策略拦截 */
    POLICY_BLOCKED("POLICY_BLOCKED"),
    /** 领域外：超出办公 IT 范围，明确告知不能答复（2026-09-29 冷启动修订新增） */
    OFF_TOPIC("OFF_TOPIC");

    @JsonValue
    private final String value;

    AiRefusalReason(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
