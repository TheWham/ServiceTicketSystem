package com.itticket.user.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 用户状态 */
public enum UserStatus {
    active("active"),
    inactive("inactive");

    @EnumValue
    @JsonValue
    private final String value;

    UserStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
