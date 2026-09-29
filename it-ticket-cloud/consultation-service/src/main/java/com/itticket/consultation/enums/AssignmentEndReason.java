package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 分配结束原因(DM-002)。 */
public enum AssignmentEndReason {
    RESPONDED("RESPONDED"),
    TIMEOUT("TIMEOUT"),
    TRANSFERRED("TRANSFERRED"),
    CANCELLED("CANCELLED"),
    COMPLETED("COMPLETED");

    @EnumValue
    @JsonValue
    private final String value;

    AssignmentEndReason(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
