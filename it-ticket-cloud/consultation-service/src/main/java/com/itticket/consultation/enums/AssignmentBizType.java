package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 分配对象类型(DM-002)。本服务只产生 CONSULTATION。 */
public enum AssignmentBizType {
    CONSULTATION("CONSULTATION"),
    TICKET("TICKET");

    @EnumValue
    @JsonValue
    private final String value;

    AssignmentBizType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
