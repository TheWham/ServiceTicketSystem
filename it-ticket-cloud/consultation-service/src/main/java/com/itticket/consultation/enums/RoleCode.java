package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 角色(DM-002)。 */
public enum RoleCode {
    EMPLOYEE("EMPLOYEE"),
    ENGINEER("ENGINEER"),
    PLATFORM_ADMIN("PLATFORM_ADMIN"),
    KNOWLEDGE_ADMIN("KNOWLEDGE_ADMIN");

    @EnumValue
    @JsonValue
    private final String value;

    RoleCode(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
