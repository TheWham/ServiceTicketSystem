package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 工程师在线状态(DM-002)。PRD 6.2:只有 AVAILABLE 可分配新咨询。 */
public enum EngineerPresence {
    AVAILABLE("AVAILABLE"),
    BUSY("BUSY"),
    AWAY("AWAY"),
    OFFLINE("OFFLINE");

    @EnumValue
    @JsonValue
    private final String value;

    EngineerPresence(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
