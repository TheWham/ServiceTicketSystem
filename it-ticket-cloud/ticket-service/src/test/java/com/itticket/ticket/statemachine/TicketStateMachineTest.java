package com.itticket.ticket.statemachine;

import com.itticket.ticket.enums.TicketStatus;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** 状态机行为回归测试（PRD-Ultimate §9.3 状态转换表） */
class TicketStateMachineTest {

    @Test
    void newToAssigned_route_system() {
        var r = TicketStateMachine.validateTransition(TicketStatus.NEW, TicketStatus.ASSIGNED, "system", "route");
        assertTrue(r.isValid());
        assertEquals("route", r.getTransition().action());
    }

    @Test
    void newRouteFailed_selfLoop_system() {
        var r = TicketStateMachine.validateTransition(TicketStatus.NEW, TicketStatus.NEW, "system", "route_failed");
        assertTrue(r.isValid());
        assertEquals("route_failed", r.getTransition().action());
    }

    @Test
    void assignedToInProgress_accept_engineer() {
        var r = TicketStateMachine.validateTransition(TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, "ENGINEER", "accept");
        assertTrue(r.isValid());
    }

    @Test
    void assignedResponseTimeout_selfLoop_system() {
        var r = TicketStateMachine.validateTransition(TicketStatus.ASSIGNED, TicketStatus.ASSIGNED, "system", "response_timeout");
        assertTrue(r.isValid());
    }

    @Test
    void inProgressToPendingSupplement_engineer() {
        var r = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING_SUPPLEMENT, "ENGINEER", "request_supplement");
        assertTrue(r.isValid());
    }

    @Test
    void pendingAcceptance_reject_employee_backToInProgress() {
        // 验收驳回不占独立状态，返回 IN_PROGRESS
        var r = TicketStateMachine.validateTransition(TicketStatus.PENDING_ACCEPTANCE, TicketStatus.IN_PROGRESS, "EMPLOYEE", "reject");
        assertTrue(r.isValid());
        assertEquals("reject", r.getTransition().action());
    }

    @Test
    void universal_cancel_anyNonTerminal_employee() {
        // 任意非终态员工可撤销（通用边）
        for (TicketStatus s : new TicketStatus[]{TicketStatus.NEW, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS}) {
            var r = TicketStateMachine.validateTransition(s, TicketStatus.CANCELLED, "EMPLOYEE", "cancel");
            assertTrue(r.isValid(), s + " 应允许员工撤销");
        }
    }

    @Test
    void universal_abnormalClose_onlyPlatformAdmin() {
        var ok = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.CLOSED, "platform_admin", "abnormal_close");
        assertTrue(ok.isValid());
        var forbidden = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.CLOSED, "ENGINEER", "abnormal_close");
        assertFalse(forbidden.isValid());
    }

    @Test
    void terminalCompleted_reopen_employee() {
        var r = TicketStateMachine.validateTransition(TicketStatus.COMPLETED, TicketStatus.IN_PROGRESS, "EMPLOYEE", "reopen");
        assertTrue(r.isValid());
    }

    @Test
    void terminalCancelled_noTransition() {
        var r = TicketStateMachine.validateTransition(TicketStatus.CANCELLED, TicketStatus.IN_PROGRESS, "EMPLOYEE", "reopen");
        assertFalse(r.isValid());
        assertEquals("当前状态「CANCELLED」已是终态或不可操作", r.getMsg());
    }

    @Test
    void engineerCannotSubmitResolutionAsEmployee() {
        var r = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING_ACCEPTANCE, "EMPLOYEE", "submit_resolution");
        assertFalse(r.isValid());
        assertTrue(r.getMsg().contains("无权"));
    }

    @Test
    void eventTypeMapping() {
        assertEquals("ASSIGNED", TicketStateMachine.getEventType("route"));
        assertEquals("ACCEPTANCE_REJECTED", TicketStateMachine.getEventType("reject"));
        assertEquals("AUTO_ACCEPTED", TicketStateMachine.getEventType("auto_accept"));
        assertEquals("SUPPLEMENT_TIMEOUT_CLOSED", TicketStateMachine.getEventType("supplement_timeout"));
        assertEquals("ROUTE_FAILED", TicketStateMachine.getEventType("route_failed"));
    }
}
