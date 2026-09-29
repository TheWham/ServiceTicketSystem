package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 知识风险级别(DM-002)。 */
public enum KnowledgeRiskLevel {
    NORMAL("NORMAL"),
    HIGH("HIGH");

    @EnumValue
    @JsonValue
    private final String value;

    KnowledgeRiskLevel(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
