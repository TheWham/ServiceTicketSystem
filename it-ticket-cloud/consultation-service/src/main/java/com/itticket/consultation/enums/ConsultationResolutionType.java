package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 咨询解决方式(DM-002)。 */
public enum ConsultationResolutionType {
    EMPLOYEE_CONFIRMED("EMPLOYEE_CONFIRMED"),
    AUTO_RESOLVED("AUTO_RESOLVED");

    @EnumValue
    @JsonValue
    private final String value;

    ConsultationResolutionType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
