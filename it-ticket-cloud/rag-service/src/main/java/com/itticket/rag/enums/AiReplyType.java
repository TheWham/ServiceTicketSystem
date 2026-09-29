package com.itticket.rag.enums;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * AI 回答类型 —— 契约 AI-003 值域。
 */
public enum AiReplyType {
    /** 正常回答，必须至少带一条知识引用 */
    ANSWER("ANSWER"),
    /** 需要澄清的问题 */
    CLARIFY("CLARIFY"),
    /** 拒答，必须给出结构化拒答原因 */
    REFUSE("REFUSE");

    @JsonValue
    private final String value;

    AiReplyType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
