package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * AI 拒答原因(AI-003)。拒答必须有结构化原因(AI-001)。
 *
 * <p>{@code OFF_TOPIC} 是 2026-09-29 策略修订新增:员工咨询 IT 办公之外的主题时,
 * AI 明确告知"不能答复"并引导转人工/提单,与"知识库无依据"(NO_RELIABLE_KNOWLEDGE)
 * 区分开,便于运营统计冷启动期知识缺口与超范围咨询的占比。
 */
public enum AiRefusalReason {
    NO_RELIABLE_KNOWLEDGE("NO_RELIABLE_KNOWLEDGE"),
    LOW_CONFIDENCE("LOW_CONFIDENCE"),
    CONFLICTING_KNOWLEDGE("CONFLICTING_KNOWLEDGE"),
    HIGH_RISK_TOPIC("HIGH_RISK_TOPIC"),
    MODEL_UNAVAILABLE("MODEL_UNAVAILABLE"),
    POLICY_BLOCKED("POLICY_BLOCKED"),
    OFF_TOPIC("OFF_TOPIC");

    @EnumValue
    @JsonValue
    private final String value;

    AiRefusalReason(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
