package com.itticket.rag.enums;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * AI 结构化拒答原因 —— 契约 AI-003 / AI-004.3 值域（6 值）。
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
    /** 高风险主题：账号权限/安全事件/数据丢失/高风险命令/硬件拆修（AI-001） */
    HIGH_RISK_TOPIC("HIGH_RISK_TOPIC"),
    /** 模型或向量服务不可用（RD-006 降级） */
    MODEL_UNAVAILABLE("MODEL_UNAVAILABLE"),
    /** 策略拦截 */
    POLICY_BLOCKED("POLICY_BLOCKED");

    @JsonValue
    private final String value;

    AiRefusalReason(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
