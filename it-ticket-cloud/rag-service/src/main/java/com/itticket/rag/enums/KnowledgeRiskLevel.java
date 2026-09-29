package com.itticket.rag.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

public enum KnowledgeRiskLevel {
    NORMAL("NORMAL"),
    LOW("LOW"),
    MEDIUM("MEDIUM"),
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
