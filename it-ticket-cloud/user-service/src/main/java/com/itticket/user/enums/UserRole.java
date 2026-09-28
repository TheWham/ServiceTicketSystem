package com.itticket.user.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 用户角色 —— 库值与 JSON 值均为英文小写,与旧版一致 */
public enum UserRole {
    employee("employee"),
    engineer("engineer"),
    supervisor("supervisor"),
    /** 人工客服:承接 AI 无法解决的咨询,决定是否转工单 */
    customer_service("customer_service");

    @EnumValue
    @JsonValue
    private final String value;

    UserRole(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
