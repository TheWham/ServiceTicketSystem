package com.itticket.ticket.statemachine;

import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.enums.TicketStatus;
import lombok.Getter;
import lombok.RequiredArgsConstructor;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 工单状态机引擎 —— 移植旧版 stateMachine.js,消息文案逐字一致。
 */
public final class TicketStateMachine {

    private TicketStateMachine() {
    }

    /** 校验结果:valid=false 时 msg 与旧版逐字一致 */
    @Getter
    @RequiredArgsConstructor
    public static class ValidationResult {
        private final boolean valid;
        private final String msg;
        private final Transition transition;

        static ValidationResult fail(String msg) {
            return new ValidationResult(false, msg, null);
        }

        static ValidationResult ok(Transition transition) {
            return new ValidationResult(true, null, transition);
        }
    }

    /** 校验状态转移是否合法;action 可选:指定后精确匹配该动作 */
    public static ValidationResult validateTransition(TicketStatus fromStatus, TicketStatus toStatus, String userRole, String action) {
        List<Transition> allowed = Transition.from(fromStatus);
        if (allowed.isEmpty()) {
            return ValidationResult.fail("当前状态「" + fromStatus.getValue() + "」已是终态或不可操作");
        }

        List<Transition> candidates = allowed.stream()
                .filter(t -> t.to() == toStatus && (action == null || t.action().equals(action)))
                .toList();

        if (candidates.isEmpty()) {
            String allowedTo = allowed.stream().map(t -> t.to().getValue()).collect(Collectors.joining("、"));
            return ValidationResult.fail("不允许从「" + fromStatus.getValue() + "」转到「" + toStatus.getValue()
                    + "」，允许的目标状态：" + allowedTo);
        }

        // 同一目标状态可能对应多个动作(如 assign / claim),优先选当前角色有权执行的
        Transition match = candidates.stream()
                .filter(t -> t.roles().contains(userRole) || t.roles().contains("system"))
                .findFirst().orElse(null);

        if (match == null) {
            String requiredRoles = candidates.stream()
                    .flatMap(t -> t.roles().stream())
                    .collect(Collectors.toCollection(LinkedHashSet::new))
                    .stream().collect(Collectors.joining(" 或 "));
            return ValidationResult.fail("角色「" + userRole + "」无权执行此操作（需要 " + requiredRoles + "）");
        }

        return ValidationResult.ok(match);
    }

    /** action → 通知事件类型,与旧版 getEventType 一致 */
    public static String getEventType(String action) {
        return switch (action == null ? "" : action) {
            case "assign", "claim" -> "DISPATCH";
            case "cancel" -> "CANCEL";
            case "need_info" -> "PENDING_SUPPLEMENT";
            case "external" -> "PENDING_EXTERNAL";
            case "done" -> "PENDING_ACCEPTANCE";
            case "accept", "auto_accept" -> "ACCEPT_APPROVED";
            case "reject" -> "ACCEPT_REJECTED";
            case "supply_info" -> "INFO_SUPPLIED";
            case "timeout" -> "TIMEOUT_CANCEL";
            case "external_resolved" -> "EXTERNAL_RESOLVED";
            default -> "STATUS_CHANGED";
        };
    }

    /** 通知接收人,与旧版 getNotifyReceivers 一致(ticket 为更新后的状态) */
    public static List<String> getNotifyReceivers(Ticket ticket, TicketStatus toStatus) {
        List<String> receivers = new java.util.ArrayList<>();
        if (toStatus == TicketStatus.PROCESSING && ticket.getAssigneeId() != null) {
            receivers.add(ticket.getAssigneeId());
        }
        if (toStatus == TicketStatus.NEED_INFO || toStatus == TicketStatus.ACCEPTANCE) {
            receivers.add(ticket.getCreatorId());
        }
        if (toStatus == TicketStatus.EXTERNAL) {
            receivers.add(ticket.getCreatorId());
            if (ticket.getAssigneeId() != null) receivers.add(ticket.getAssigneeId());
        }
        if (toStatus == TicketStatus.DONE || toStatus == TicketStatus.CANCELLED) {
            receivers.add(ticket.getCreatorId());
            if (ticket.getAssigneeId() != null) receivers.add(ticket.getAssigneeId());
        }
        return receivers;
    }
}
