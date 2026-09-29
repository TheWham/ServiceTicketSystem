package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** SLA 状态(DM-002)。 */
public enum SlaStatus {
    RUNNING("RUNNING"),
    PAUSED("PAUSED"),
    MET("MET"),
    BREACHED("BREACHED"),
    CANCELLED("CANCELLED");

    @EnumValue
    @JsonValue
    private final String value;

    SlaStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
