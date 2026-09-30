package com.itticket.rag.enums;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * 办公 IT 领域判定结果 —— 契约 MR-004（specs/10-model-rag-integration.md:70）。
 *
 * <p>领域判定独立于生成结果；检索资料和用户输入均不得覆盖领域规则
 * （AI-001 · specs/02-ai-api-json-schema.md:14：单个 IT 关键词或检索命中不构成领域许可）。</p>
 */
public enum OfficeDomain {
    /** 办公 IT 范围内：允许检索，无命中也可给通用建议（AI-001） */
    OFFICE_IT("OFFICE_IT"),
    /** 领域外或混合含非 IT 任务：必须 REFUSE + OFF_TOPIC */
    OFF_TOPIC("OFF_TOPIC"),
    /** 高风险操作：权限变更、安全事件处置、数据恢复、高风险命令、硬件拆修 */
    HIGH_RISK("HIGH_RISK"),
    /** 语义不明确：返回不含解决步骤的 CLARIFY */
    UNCERTAIN("UNCERTAIN");

    @JsonValue
    private final String value;

    OfficeDomain(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
