package com.itticket.ticket.statemachine;

import com.itticket.ticket.enums.TicketStatus;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 状态转移规则 —— 逐条对应 PRD-Ultimate §9.3 状态转换表（18 条边）。
 * 守卫条件（补充事项非空/驳回原因必填/撤销原因必填/依赖信息必填等）在
 * TicketService.action 中显式校验，此处仅保留规则元数据。
 * 角色：employee 员工 / engineer 工程师 / platform_admin 平台管理员 / system 系统
 */
public record Transition(TicketStatus to, String action, Set<String> roles, String remark) {

    public static Transition of(TicketStatus to, String action, String remark, String... roles) {
        return new Transition(to, action, Set.of(roles), remark);
    }

    /** 每个状态允许转出的规则列表 */
    public static List<Transition> from(TicketStatus status) {
        return TRANSITIONS.getOrDefault(status, List.of());
    }

    /** 通用边：任意非终态 → 员工撤销 / 管理员异常关闭 / 管理员标记重复单 */
    public static List<Transition> universal() {
        return UNIVERSAL;
    }

    private static final List<Transition> UNIVERSAL = List.of(
            Transition.of(TicketStatus.CANCELLED, "cancel", "主动撤销（原因必填）", "employee"),
            Transition.of(TicketStatus.CLOSED, "abnormal_close", "异常关闭（原因必填）", "platform_admin"),
            Transition.of(TicketStatus.CLOSED, "mark_duplicate", "标记重复单（关联主工单）", "platform_admin"));

    private static final Map<TicketStatus, List<Transition>> TRANSITIONS = Map.of(
            // NEW：路由成功 / 无候选人（自环入异常队列）/ 撤销
            TicketStatus.NEW, List.of(
                    Transition.of(TicketStatus.ASSIGNED, "route", "路由成功，记录工程师与响应截止", "system"),
                    Transition.of(TicketStatus.NEW, "route_failed", "无可用候选人，进入异常队列", "system")),
            // ASSIGNED：接单 / 响应超时转派（自环）
            TicketStatus.ASSIGNED, List.of(
                    Transition.of(TicketStatus.IN_PROGRESS, "accept", "工程师接单，确认影响与紧急程度", "engineer"),
                    Transition.of(TicketStatus.ASSIGNED, "response_timeout", "响应超时转派下一名", "system")),
            // IN_PROGRESS：请求补充 / 等待外部 / 提交解决方案
            TicketStatus.IN_PROGRESS, List.of(
                    Transition.of(TicketStatus.PENDING_SUPPLEMENT, "request_supplement", "请求补充（事项必填）", "engineer"),
                    Transition.of(TicketStatus.PENDING_EXTERNAL, "external_wait", "等待外部（类型/原因/预计时间必填）", "engineer"),
                    Transition.of(TicketStatus.PENDING_ACCEPTANCE, "submit_resolution", "提交解决方案（方案+验证结果必填）", "engineer")),
            // PENDING_SUPPLEMENT：员工补充 / 72h 未补充自动关闭
            TicketStatus.PENDING_SUPPLEMENT, List.of(
                    Transition.of(TicketStatus.IN_PROGRESS, "supply_info", "员工补充（实际提交内容）", "employee"),
                    Transition.of(TicketStatus.CLOSED, "supplement_timeout", "72小时未补充自动关闭", "system")),
            // PENDING_EXTERNAL：外部条件恢复
            TicketStatus.PENDING_EXTERNAL, List.of(
                    Transition.of(TicketStatus.IN_PROGRESS, "external_resolved", "外部条件恢复（填写恢复说明）", "engineer")),
            // PENDING_ACCEPTANCE：验收通过 / 48h 自动验收 / 验收驳回
            TicketStatus.PENDING_ACCEPTANCE, List.of(
                    Transition.of(TicketStatus.COMPLETED, "accept", "员工验收通过（可选评价）", "employee"),
                    Transition.of(TicketStatus.COMPLETED, "auto_accept", "48小时未操作自动验收", "system"),
                    Transition.of(TicketStatus.IN_PROGRESS, "reject", "验收驳回（原因必填，从原累计耗时继续）", "employee")),
            // COMPLETED：7 日内同一问题复发重新打开
            TicketStatus.COMPLETED, List.of(
                    Transition.of(TicketStatus.IN_PROGRESS, "reopen", "7日内同一问题复发重新打开", "employee")),
            // CLOSED：规则允许恢复（逾期补充由员工 / 误判与异常关闭由管理员）
            TicketStatus.CLOSED, List.of(
                    Transition.of(TicketStatus.IN_PROGRESS, "reopen_supplement", "逾期补充关闭，7日内员工补齐恢复", "employee"),
                    Transition.of(TicketStatus.IN_PROGRESS, "reopen_admin", "误判/异常关闭，管理员重新打开", "platform_admin"))
    );
}
