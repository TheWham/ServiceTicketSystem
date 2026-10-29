package com.itticket.ticket.statemachine;

import com.itticket.ticket.enums.TicketStatus;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 工单状态机行为回归测试（对齐 PRD-Ultimate §9.3 状态转换表）。
 *
 * 主链路：NEW ->(route)-> ASSIGNED ->(accept)-> IN_PROGRESS ->(submit_resolution)->
 *         PENDING_ACCEPTANCE ->(accept)-> COMPLETED
 * 分支：request_supplement / reject 回到 IN_PROGRESS；外部等待挂起与恢复；
 *       cancel 为任意非终态通用边；abnormal_close 仅 PLATFORM_ADMIN；
 *       COMPLETED 允许员工 reopen；CANCELLED 为绝对终态。
 * 每条用例名 = "起始状态->目标状态_动作_发起角色"。
 */
class TicketStateMachineTest {

    /** 系统路由成功：NEW -> ASSIGNED，动作编码 route 须原样返回供流转日志使用 */
    @Test
    void newToAssigned_route_system() {
        var r = TicketStateMachine.validateTransition(TicketStatus.NEW, TicketStatus.ASSIGNED, "system", "route");
        assertTrue(r.isValid());
        assertEquals("route", r.getTransition().action());
    }

    /** 路由失败是 NEW -> NEW 的自环（工单留在待派单池等待人工/重试），动作 route_failed */
    @Test
    void newRouteFailed_selfLoop_system() {
        var r = TicketStateMachine.validateTransition(TicketStatus.NEW, TicketStatus.NEW, "system", "route_failed");
        assertTrue(r.isValid());
        assertEquals("route_failed", r.getTransition().action());
    }

    /** 工程师接单：ASSIGNED -> IN_PROGRESS（仅工程师角色可执行 accept） */
    @Test
    void assignedToInProgress_accept_engineer() {
        var r = TicketStateMachine.validateTransition(TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, "ENGINEER", "accept");
        assertTrue(r.isValid());
    }

    /** 响应超时未接单：ASSIGNED -> ASSIGNED 自环（由系统自动改派，状态本身不变） */
    @Test
    void assignedResponseTimeout_selfLoop_system() {
        var r = TicketStateMachine.validateTransition(TicketStatus.ASSIGNED, TicketStatus.ASSIGNED, "system", "response_timeout");
        assertTrue(r.isValid());
    }

    /** 工程师要求员工补充材料：IN_PROGRESS -> PENDING_SUPPLEMENT */
    @Test
    void inProgressToPendingSupplement_engineer() {
        var r = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING_SUPPLEMENT, "ENGINEER", "request_supplement");
        assertTrue(r.isValid());
    }

    /** 员工验收驳回不占独立状态，直接回到 IN_PROGRESS 由工程师继续处理 */
    @Test
    void pendingAcceptance_reject_employee_backToInProgress() {
        // 验收驳回不占独立状态，返回 IN_PROGRESS
        var r = TicketStateMachine.validateTransition(TicketStatus.PENDING_ACCEPTANCE, TicketStatus.IN_PROGRESS, "EMPLOYEE", "reject");
        assertTrue(r.isValid());
        assertEquals("reject", r.getTransition().action());
    }

    /** 通用边：任意非终态（抽验 NEW/ASSIGNED/IN_PROGRESS）员工都可撤销工单 */
    @Test
    void universal_cancel_anyNonTerminal_employee() {
        // 任意非终态员工可撤销（通用边）
        for (TicketStatus s : new TicketStatus[]{TicketStatus.NEW, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS}) {
            var r = TicketStateMachine.validateTransition(s, TicketStatus.CANCELLED, "EMPLOYEE", "cancel");
            assertTrue(r.isValid(), s + " 应允许员工撤销");
        }
    }

    /** 异常关闭是 PLATFORM_ADMIN 专属动作：管理员放行、工程师必拒 */
    @Test
    void universal_abnormalClose_onlyPlatformAdmin() {
        var ok = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.CLOSED, "platform_admin", "abnormal_close");
        assertTrue(ok.isValid());
        var forbidden = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.CLOSED, "ENGINEER", "abnormal_close");
        assertFalse(forbidden.isValid());
    }

    /** 已完成的工单允许员工 reopen 重新打开（验收后发现未解决） */
    @Test
    void terminalCompleted_reopen_employee() {
        var r = TicketStateMachine.validateTransition(TicketStatus.COMPLETED, TicketStatus.IN_PROGRESS, "EMPLOYEE", "reopen");
        assertTrue(r.isValid());
    }

    /** 已撤销是绝对终态：任何迁移被拒，且报错文案明确告知终态不可操作 */
    @Test
    void terminalCancelled_noTransition() {
        var r = TicketStateMachine.validateTransition(TicketStatus.CANCELLED, TicketStatus.IN_PROGRESS, "EMPLOYEE", "reopen");
        assertFalse(r.isValid());
        assertEquals("当前状态「CANCELLED」已是终态或不可操作", r.getMsg());
    }

    /** 越权迁移：员工执行工程师专属的 submit_resolution，拒绝且提示“无权” */
    @Test
    void engineerCannotSubmitResolutionAsEmployee() {
        var r = TicketStateMachine.validateTransition(TicketStatus.IN_PROGRESS, TicketStatus.PENDING_ACCEPTANCE, "EMPLOYEE", "submit_resolution");
        assertFalse(r.isValid());
        assertTrue(r.getMsg().contains("无权"));
    }

    /**
     * 动作 -> 历史事件类型映射（getEventType 供旧版流转记录兼容查询）：
     * 几个高频动作的映射必须稳定，前端时间线按事件类型渲染图标与文案。
     */
    @Test
    void eventTypeMapping() {
        assertEquals("ASSIGNED", TicketStateMachine.getEventType("route"));
        assertEquals("ACCEPTANCE_REJECTED", TicketStateMachine.getEventType("reject"));
        assertEquals("AUTO_ACCEPTED", TicketStateMachine.getEventType("auto_accept"));
        assertEquals("SUPPLEMENT_TIMEOUT_CLOSED", TicketStateMachine.getEventType("supplement_timeout"));
        assertEquals("ROUTE_FAILED", TicketStateMachine.getEventType("route_failed"));
    }
}