package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 消息发送方类型(DM-002)。 */
public enum MessageSenderType {
    EMPLOYEE("EMPLOYEE"),
    ENGINEER("ENGINEER"),
    AI("AI"),
    SYSTEM("SYSTEM");

    @EnumValue
    @JsonValue
    private final String value;

    MessageSenderType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
