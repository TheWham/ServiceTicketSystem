package com.itticket.rag.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

public enum KnowledgeStatus {
    DRAFT("DRAFT"),
    SUBMITTED("SUBMITTED"),
    REVIEWED("REVIEWED"),
    PUBLISHED("PUBLISHED"),
    ARCHIVED("ARCHIVED");

    @EnumValue
    @JsonValue
    private final String value;

    KnowledgeStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
