package com.itticket.ticket.statemachine;

import com.itticket.ticket.enums.TicketStatus;

import java.util.List;
import java.util.Set;

/**
 * 状态转移规则 —— 逐条对应旧版 stateMachine.js 的 TRANSITIONS。
 * 旧版 guard(reject_reason_10 / has_remark_10 / has_flow_log / no_flow_log)实际在
 * TicketService.action 中以显式校验实现,此处仅保留规则元数据。
 */
public record Transition(TicketStatus to, String action, Set<String> roles, String remark) {

    public static Transition of(TicketStatus to, String action, String remark, String... roles) {
        return new Transition(to, action, Set.of(roles), remark);
    }

    /** 每个状态允许转出的规则列表 */
    public static List<Transition> from(TicketStatus status) {
        return TRANSITIONS.getOrDefault(status, List.of());
    }

    private static final java.util.Map<TicketStatus, List<Transition>> TRANSITIONS = java.util.Map.of(
            TicketStatus.PENDING, List.of(
                    // 派单(主管)与领取(工程师)等价,只是操作者不同
                    Transition.of(TicketStatus.PROCESSING, "assign", "派单", "supervisor"),
                    Transition.of(TicketStatus.PROCESSING, "claim", "领取工单", "engineer"),
                    Transition.of(TicketStatus.CANCELLED, "cancel", "撤回", "employee")),
            TicketStatus.PROCESSING, List.of(
                    Transition.of(TicketStatus.NEED_INFO, "need_info", "申请补充信息", "engineer"),
                    Transition.of(TicketStatus.EXTERNAL, "external", "需外部支持", "engineer"),
                    Transition.of(TicketStatus.ACCEPTANCE, "done", "提交方案", "engineer")),
            TicketStatus.NEED_INFO, List.of(
                    Transition.of(TicketStatus.PROCESSING, "supply_info", "补充信息", "employee"),
                    Transition.of(TicketStatus.CANCELLED, "timeout", "超时未补充", "system")),
            TicketStatus.EXTERNAL, List.of(
                    Transition.of(TicketStatus.PROCESSING, "external_resolved", "外部解除", "engineer", "supervisor")),
            TicketStatus.ACCEPTANCE, List.of(
                    Transition.of(TicketStatus.DONE, "accept", "验收通过", "employee"),
                    Transition.of(TicketStatus.PROCESSING, "reject", "驳回", "employee"),
                    Transition.of(TicketStatus.DONE, "auto_accept", "超时自动通过(3工作日)", "system"))
    );
}
