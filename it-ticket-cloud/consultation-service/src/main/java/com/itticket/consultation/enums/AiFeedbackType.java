package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** AI 反馈类型(DM-002 AiFeedbackType,等同 AI-003 FeedbackType)。 */
public enum AiFeedbackType {
    HELPFUL("HELPFUL"),
    NOT_HELPFUL("NOT_HELPFUL"),
    INCORRECT("INCORRECT");

    @EnumValue
    @JsonValue
    private final String value;

    AiFeedbackType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
