package com.itticket.ticket.statemachine;

import com.itticket.ticket.enums.TicketStatus;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** 状态机行为与旧版 stateMachine.js 对齐的回归测试 */
class TicketStateMachineTest {

    @Test
    void pendingToProcessing_assign_supervisor() {
        var r = TicketStateMachine.validateTransition(TicketStatus.PENDING, TicketStatus.PROCESSING, "supervisor", "assign");
        assertTrue(r.isValid());
        assertEquals("assign", r.getTransition().action());
    }

    @Test
    void pendingToProcessing_claim_engineer() {
        var r = TicketStateMachine.validateTransition(TicketStatus.PENDING, TicketStatus.PROCESSING, "engineer", "claim");
        assertTrue(r.isValid());
        assertEquals("claim", r.getTransition().action());
    }

    @Test
    void pendingCancel_engineerForbidden_msgMatchesLegacy() {
        // engineer 想转 PROCESSING 时若只允许 assign,提示「需要 supervisor」;employee 无权 assign
        var r = TicketStateMachine.validateTransition(TicketStatus.PENDING, TicketStatus.PROCESSING, "employee", null);
        assertFalse(r.isValid());
        assertEquals("角色「employee」无权执行此操作（需要 supervisor 或 engineer）", r.getMsg());
    }

    @Test
    void terminalStatus_msgMatchesLegacy() {
        var r = TicketStateMachine.validateTransition(TicketStatus.DONE, TicketStatus.PROCESSING, "engineer", "progress");
        assertFalse(r.isValid());
        assertEquals("当前状态「已完成」已是终态或不可操作", r.getMsg());
    }

    @Test
    void illegalTarget_msgMatchesLegacy() {
        var r = TicketStateMachine.validateTransition(TicketStatus.PENDING, TicketStatus.DONE, "employee", "done");
        assertFalse(r.isValid());
        assertEquals("不允许从「待处理」转到「已完成」，允许的目标状态：处理中、处理中、已取消", r.getMsg());
    }

    @Test
    void eventTypeMapping() {
        assertEquals("DISPATCH", TicketStateMachine.getEventType("claim"));
        assertEquals("ACCEPT_APPROVED", TicketStateMachine.getEventType("accept"));
        assertEquals("STATUS_CHANGED", TicketStateMachine.getEventType("unknown"));
    }

    @Test
    void notifyReceivers_processing_goesToAssignee() {
        var ticket = new com.itticket.ticket.entity.Ticket();
        ticket.setCreatorId("U001");
        ticket.setAssigneeId("U004");
        var receivers = TicketStateMachine.getNotifyReceivers(ticket, TicketStatus.PROCESSING);
        assertEquals(1, receivers.size());
        assertEquals("U004", receivers.get(0));
    }
}
