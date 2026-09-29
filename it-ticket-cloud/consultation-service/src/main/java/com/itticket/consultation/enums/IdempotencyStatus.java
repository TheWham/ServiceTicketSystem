package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 幂等记录状态(DM-002)。 */
public enum IdempotencyStatus {
    IN_PROGRESS("IN_PROGRESS"),
    SUCCEEDED("SUCCEEDED"),
    FAILED("FAILED");

    @EnumValue
    @JsonValue
    private final String value;

    IdempotencyStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
