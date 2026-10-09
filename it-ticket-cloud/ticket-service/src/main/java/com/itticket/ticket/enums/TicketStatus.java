package com.itticket.ticket.enums;

import com.baomidou.mybatisplus.annotation.EnumValue;
import com.fasterxml.jackson.annotation.JsonValue;

/**
 * 工单状态 —— PRD-Ultimate §9.2，共 9 态。
 * 库值与 JSON 值均为英文枚举名（与 PRD §26「状态枚举只能使用本文定义的值」一致）。
 * 旧版 7 态中文枚举已废弃；验收驳回不占独立状态，而是 PENDING_ACCEPTANCE→IN_PROGRESS 的流转事件。
 */
public enum TicketStatus {
    /** 已提交，系统正在路由 */
    NEW("NEW", "已提交待路由", false),
    /** 已分配，等待工程师接单 */
    ASSIGNED("ASSIGNED", "已分配", false),
    /** 工程师正在处理 */
    IN_PROGRESS("IN_PROGRESS", "处理中", false),
    /** 等待员工补充 */
    PENDING_SUPPLEMENT("PENDING_SUPPLEMENT", "待补充", false),
    /** 等待备件/厂商/运营商或其他外部执行条件 */
    PENDING_EXTERNAL("PENDING_EXTERNAL", "待外部", false),
    /** 已提交解决方案，等待员工验收 */
    PENDING_ACCEPTANCE("PENDING_ACCEPTANCE", "待验收", false),
    /** 已验收或自动验收（可按规则重新打开） */
    COMPLETED("COMPLETED", "已完成", true),
    /** 员工主动撤销（不可恢复） */
    CANCELLED("CANCELLED", "已撤回", true),
    /** 逾期未补充/重复单/管理员异常关闭（部分原因可恢复） */
    CLOSED("CLOSED", "已关闭", true);

    @EnumValue
    @JsonValue
    private final String value;

    /** 中文展示名 */
    private final String label;

    /** 是否终态 */
    private final boolean terminal;

    TicketStatus(String value, String label, boolean terminal) {
        this.value = value;
        this.label = label;
        this.terminal = terminal;
    }

    public String getValue() {
        return value;
    }

    public String getLabel() {
        return label;
    }

    public boolean isTerminal() {
        return terminal;
    }

    /** 按字符串解析（兼容旧数据中文值） */
    public static TicketStatus fromValue(String v) {
        if (v == null) return null;
        for (TicketStatus s : values()) {
            if (s.value.equalsIgnoreCase(v) || s.label.equals(v)) return s;
        }
        return null;
    }
}
