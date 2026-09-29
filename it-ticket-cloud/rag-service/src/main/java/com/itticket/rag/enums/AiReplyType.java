package com.itticket.rag.enums;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * AI 回答类型 —— 契约 AI-003（docs/specs/02-ai-api-json-schema.md）。
 *
 * <p>本模块只负责检索与领域判定，最终 replyType 由 AI 客服服务决定；
 * 本枚举仅作为检索响应中的建议提示，不构成决策。</p>
 */
public enum AiReplyType {
    /** 正常回答：带真实知识引用，或空引用表示通用回答（AI-001 冷启动修订） */
    ANSWER("ANSWER"),
    /** 追问澄清：不含解决步骤 */
    CLARIFY("CLARIFY"),
    /** 拒答：必须给出结构化拒答原因 */
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
