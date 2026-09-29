package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 咨询状态(DM-002)。终态见 SM-CONSULT-001,仅 RESOLVED 允许 24 小时内恢复。 */
public enum ConsultationStatus {
    AI_ACTIVE("AI_ACTIVE"),
    WAITING_ENGINEER("WAITING_ENGINEER"),
    HUMAN_ACTIVE("HUMAN_ACTIVE"),
    PENDING_CONFIRMATION("PENDING_CONFIRMATION"),
    RESOLVED("RESOLVED"),
    CONVERTED_TO_TICKET("CONVERTED_TO_TICKET"),
    CLOSED("CLOSED");

    @EnumValue
    @JsonValue
    private final String value;

    ConsultationStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    /** SM-CONSULT-001:RESOLVED、CONVERTED_TO_TICKET、CLOSED 为终态。 */
    public boolean isTerminal() {
        return this == RESOLVED || this == CONVERTED_TO_TICKET || this == CLOSED;
    }
}
