package com.itticket.consultation.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/** 知识状态(DM-002)。AI 与搜索只允许读取 PUBLISHED。 */
public enum KnowledgeStatus {
    DRAFT("DRAFT"),
    PENDING_REVIEW("PENDING_REVIEW"),
    PUBLISHED("PUBLISHED"),
    OFFLINE("OFFLINE");

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
