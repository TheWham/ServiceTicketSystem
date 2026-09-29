package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** AI 回复类型(AI-003)。 */
public enum AiReplyType {
    ANSWER("ANSWER"),
    CLARIFY("CLARIFY"),
    REFUSE("REFUSE");

    @EnumValue
    @JsonValue
    private final String value;

    AiReplyType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
