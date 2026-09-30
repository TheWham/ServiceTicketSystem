package com.itticket.rag.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * 知识文章状态 —— 契约 SM-KNOWLEDGE-001（specs/03-business-state-machine.md:90）/
 * PRD §16.3（IT服务工单系统PRD-Ultimate.md:504）值域：DRAFT / PENDING_REVIEW / PUBLISHED / OFFLINE。
 *
 * <p>SUBMITTED / REVIEWED / ARCHIVED 为历史过渡值，仅为兼容既有数据保留，不参与状态流转；
 * 流转白名单由 {@link #isContracted()} 界定。</p>
 */
public enum KnowledgeStatus {
    /** 草稿，可编辑 */
    DRAFT("DRAFT"),
    /** 等待审核 */
    PENDING_REVIEW("PENDING_REVIEW"),
    /** 已正式发布，可进入 RAG 检索 */
    PUBLISHED("PUBLISHED"),
    /** 已下线，不再展示或检索 */
    OFFLINE("OFFLINE"),

    // 兼容历史过渡状态（不参与流转）
    @Deprecated
    SUBMITTED("SUBMITTED"),
    @Deprecated
    REVIEWED("REVIEWED"),
    @Deprecated
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

    /** 是否为契约定义的四态之一；状态机只允许在这四个值之间流转 */
    public boolean isContracted() {
        return this == DRAFT || this == PENDING_REVIEW || this == PUBLISHED || this == OFFLINE;
    }
}
