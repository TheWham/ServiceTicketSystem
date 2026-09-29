package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 咨询来源(DM-002)。 */
public enum ConsultationSource {
    AI("AI"),
    HUMAN_DIRECT("HUMAN_DIRECT"),
    TICKET_FOLLOW_UP("TICKET_FOLLOW_UP");

    @EnumValue
    @JsonValue
    private final String value;

    ConsultationSource(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
