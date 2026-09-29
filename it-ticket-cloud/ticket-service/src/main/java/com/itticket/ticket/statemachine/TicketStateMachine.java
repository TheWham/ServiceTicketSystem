package com.itticket.ticket.statemachine;

import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.enums.TicketStatus;
import lombok.Getter;
import lombok.RequiredArgsConstructor;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 工单状态机引擎 —— PRD-Ultimate §9.3。
 * 通用边（撤销/异常关闭/重复单）与各状态专属边合并校验。
 */
public final class TicketStateMachine {

    private TicketStateMachine() {
    }

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

    /** 校验状态转移是否合法；action 可选：指定后精确匹配该动作 */
    public static ValidationResult validateTransition(TicketStatus fromStatus, TicketStatus toStatus, String userRole, String action) {
        // 通用边仅对非终态生效；终态只允许 COMPLETED/CLOSED 各自的恢复边
        List<Transition> allowed = new ArrayList<>(Transition.from(fromStatus));
        if (fromStatus != null && !fromStatus.isTerminal()) {
            allowed.addAll(Transition.universal());
        }
        if (allowed.isEmpty()) {
            return ValidationResult.fail("当前状态「" + fromStatus.getValue() + "」已是终态或不可操作");
        }

        List<Transition> candidates = allowed.stream()
                .filter(t -> t.to() == toStatus && (action == null || t.action().equals(action)))
                .toList();

        if (candidates.isEmpty()) {
            String allowedTo = allowed.stream().map(t -> t.to().getValue()).distinct().collect(Collectors.joining("、"));
            return ValidationResult.fail("不允许从「" + fromStatus.getValue() + "」转到「" + toStatus.getValue()
                    + "」，允许的目标状态：" + allowedTo);
        }

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

    /** action → 通知事件类型（PRD §14.2 通知事件集） */
    public static String getEventType(String action) {
        return switch (action == null ? "" : action) {
            case "route" -> "ASSIGNED";                       // 新工单分配
            case "accept" -> "ACCEPTED";                      // 接单（结合上下文区分验收，用 TICKET_ACCEPTED 区分）
            case "response_timeout" -> "RESPONSE_TIMEOUT";    // 响应超时及自动转派
            case "request_supplement" -> "SUPPLEMENT_REQUESTED";
            case "supply_info" -> "INFO_SUPPLIED";
            case "supplement_timeout" -> "SUPPLEMENT_TIMEOUT_CLOSED";
            case "external_wait" -> "EXTERNAL_WAIT";
            case "external_resolved" -> "EXTERNAL_RESOLVED";
            case "submit_resolution" -> "RESOLUTION_SUBMITTED";
            case "reject" -> "ACCEPTANCE_REJECTED";
            case "auto_accept" -> "AUTO_ACCEPTED";
            case "cancel" -> "CANCELLED";
            case "abnormal_close" -> "ABNORMAL_CLOSED";
            case "mark_duplicate" -> "MARKED_DUPLICATE";
            case "reopen", "reopen_supplement", "reopen_admin" -> "REOPENED";
            case "route_failed" -> "ROUTE_FAILED";
            default -> "STATUS_CHANGED";
        };
    }

    /** 通知接收人（ticket 为更新后的状态） */
    public static List<String> getNotifyReceivers(Ticket ticket, TicketStatus toStatus) {
        List<String> receivers = new ArrayList<>();
        if (toStatus == null || ticket == null) return receivers;
        switch (toStatus) {
            case ASSIGNED -> { // 分配给工程师
                if (ticket.getAssigneeId() != null) receivers.add(ticket.getAssigneeId());
            }
            case PENDING_SUPPLEMENT, PENDING_ACCEPTANCE -> // 需要员工行动
                receivers.add(ticket.getCreatorId());
            case PENDING_EXTERNAL -> { // 员工+工程师双方
                receivers.add(ticket.getCreatorId());
                if (ticket.getAssigneeId() != null) receivers.add(ticket.getAssigneeId());
            }
            case COMPLETED, CANCELLED, CLOSED -> { // 员工（+工程师知会）
                receivers.add(ticket.getCreatorId());
                if (ticket.getAssigneeId() != null) receivers.add(ticket.getAssigneeId());
            }
            default -> { // IN_PROGRESS 等：不主动通知
            }
        }
        return receivers;
    }
}
