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
    OFF_TOPIC("OFF_TOPIC"),
    /**
     * 能力范围外:问题本身不归这条链路管(2026-10-27 新增)。
     *
     * <p>与 {@code NO_RELIABLE_KNOWLEDGE} 刻意分开——后者是"数据不足以支撑结论",
     * 处置方向是补样本或转人工;这个是"问题根本不归这条链路管",处置方向是换入口
     * (跨工单分析收到单条故障提问时,引导去智能客服)。两者下一步动作相反,
     * 合成一个值会把工程师引错方向。
     */
    OUT_OF_SCOPE("OUT_OF_SCOPE");

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
