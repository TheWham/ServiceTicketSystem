package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** Outbox 投递状态(DM-002)。 */
public enum OutboxStatus {
    PENDING("PENDING"),
    PUBLISHED("PUBLISHED"),
    FAILED("FAILED"),
    DEAD_LETTER("DEAD_LETTER");

    @EnumValue
    @JsonValue
    private final String value;

    OutboxStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
