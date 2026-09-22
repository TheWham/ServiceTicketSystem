package com.itticket.ticket.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * 工单状态 —— 库值与 JSON 值均为中文,与旧版 SQLite/接口完全一致
 */
public enum TicketStatus {
    PENDING("待处理"),
    PROCESSING("处理中"),
    NEED_INFO("待补充"),
    EXTERNAL("待外部"),
    ACCEPTANCE("待验收"),
    DONE("已完成"),
    CANCELLED("已取消");

    @EnumValue
    @JsonValue
    private final String value;

    TicketStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
