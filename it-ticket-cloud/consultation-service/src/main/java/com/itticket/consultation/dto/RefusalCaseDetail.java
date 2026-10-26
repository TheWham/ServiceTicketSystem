package com.itticket.consultation.dto;

import java.util.List;

/** 拒答案例详情:列表项 + 会话上下文消息。 */
public record RefusalCaseDetail(
        RefusalCaseItem item,
        List<MessageProjection> contextMessages) {

    public RefusalCaseDetail {
        contextMessages = contextMessages == null ? List.of() : List.copyOf(contextMessages);
    }
}
