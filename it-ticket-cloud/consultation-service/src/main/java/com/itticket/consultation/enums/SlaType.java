package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** SLA 类型(DM-002)。本服务只产生 CONSULTATION_RESPONSE。 */
public enum SlaType {
    CONSULTATION_RESPONSE("CONSULTATION_RESPONSE"),
    TICKET_RESPONSE("TICKET_RESPONSE"),
    TICKET_COMPLETION("TICKET_COMPLETION");

    @EnumValue
    @JsonValue
    private final String value;

    SlaType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
