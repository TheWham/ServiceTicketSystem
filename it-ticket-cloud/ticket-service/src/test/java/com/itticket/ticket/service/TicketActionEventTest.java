package com.itticket.ticket.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.AcceptRequest;
import com.itticket.ticket.dto.ActionRequest;
import com.itticket.ticket.entity.Assignment;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.mockito.ArgumentCaptor;
import java.util.Set;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * 工单动作 -> 流转日志事件的映射契约（支撑“流转记录更详细”的需求）：
 *  - 每个业务动作即使起点/终点状态相同，也必须写入各自专属的事件编码
 *    （如 progress 与 reject 都终止于 IN_PROGRESS，但事件必须不同），
 *    否则前端时间线无法区分“工程师记录进展”与“员工驳回验收”；
 *  - 人工接单 / 自动验收 / 超时转派等系统动作同样有专属事件；
 *  - 超时转派是“处理人变更而非状态流转”，from/to 状态必须保持 ASSIGNED。
 */
class TicketActionEventTest {

    /** LambdaUpdateWrapper/查询条件解析依赖 MyBatis-Plus 实体元数据，纯单测需手动初始化一次 */
    @org.junit.jupiter.api.BeforeAll
    static void initializeMapping() {
        com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                new org.apache.ibatis.builder.MapperBuilderAssistant(new com.baomidou.mybatisplus.core.MybatisConfiguration(), ""), Ticket.class);
    }

    private final TicketMapper tickets = mock(TicketMapper.class);
    private final TicketFlowLogMapper flows = mock(TicketFlowLogMapper.class);
    private final SlaService sla = mock(SlaService.class);
    private final NotificationService notifications = mock(NotificationService.class);
    private final RoutingService routing = mock(RoutingService.class);
    private final TicketService service = new TicketService(tickets, mock(CategoryMapper.class), mock(AttachmentMapper.class),
            flows, mock(com.itticket.ticket.mapper.TicketPurgeMapper.class), mock(TicketNoGenerator.class), notifications,
            mock(UserClient.class), sla, routing,
            mock(ExceptionQueueService.class), mock(ConsultationConvertNotifier.class), new ObjectMapper());

    /**
     * 造一张处于指定状态的工单并配好 mock：
     * selectById 命中、条件更新返回 1 行、已有 1 条流水（用于流转序号递增）。
     */
    private Ticket ticket(TicketStatus status) {
        Ticket ticket = new Ticket();
        ticket.setTicketId("TK01");
        ticket.setStatus(status);
        ticket.setCreatorId("EMP01");
        ticket.setAssigneeId("ENG01");
        ticket.setPriority("MEDIUM");
        ticket.setCategoryId("C_NET");
        when(tickets.selectById("TK01")).thenReturn(ticket);
        when(tickets.selectOne(any())).thenReturn(ticket);
        when(tickets.update(isNull(), any())).thenReturn(1);
        when(flows.selectCount(any())).thenReturn(1L);
        return ticket;
    }

    /**
     * 核心参数化回归：9 个合法动作各自映射到专属事件编码。
     * CsvSource 每行 = 动作, 合法起始状态, 期望事件编码；
     * 再按动作归属不同角色（reject/supply_info/accept/cancel 由员工发起，其余由工程师发起）执行；
     * 断言事件编码与 from_status，并对“终点同为 IN_PROGRESS 但语义不同”的动作验证 to_status。
     */
    @ParameterizedTest
    @CsvSource({
        "progress,IN_PROGRESS,TICKET_PROGRESS",                 // 工程师记录进展（状态不变，但仍须留痕）
        "reject,PENDING_ACCEPTANCE,TICKET_REJECT_ACCEPTANCE",   // 员工驳回验收 -> 回到处理中
        "supply_info,PENDING_SUPPLEMENT,TICKET_SUBMIT_SUPPLEMENT", // 员工补材料 -> 回到处理中
        "external_resolved,PENDING_EXTERNAL,TICKET_RESUME_EXTERNAL", // 外部依赖解决 -> 恢复处理
        "need_info,IN_PROGRESS,TICKET_REQUEST_SUPPLEMENT",      // 工程师要求补材料
        "external,IN_PROGRESS,TICKET_START_EXTERNAL_WAIT",      // 挂起等待外部
        "done,IN_PROGRESS,TICKET_SUBMIT_RESOLUTION",            // 工程师提交解决方案
        "accept,PENDING_ACCEPTANCE,TICKET_APPROVE_ACCEPTANCE",  // 员工验收通过
        "cancel,NEW,TICKET_CANCEL"                              // 员工撤单
    })
    void actionWritesItsOwnEventEvenWhenTargetStateIsShared(String action, TicketStatus from, String event) {
        ticket(from);
        ActionRequest request = new ActionRequest();
        request.setAction(action);
        request.setRemark("Sufficient detail for this action");
        boolean employeeAction = Set.of("reject", "supply_info", "accept", "cancel").contains(action);
        UserContext.CurrentUser user = new UserContext.CurrentUser(employeeAction ? "EMP01" : "ENG01", "User",
                employeeAction ? "EMPLOYEE" : "ENGINEER", "IT");
        service.action(user, "TK01", request);
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(captured.capture());
        assertEquals(event, captured.getValue().getEvent());
        assertEquals(from.getValue(), captured.getValue().getFromStatus());
        // 这几个动作终点同为 IN_PROGRESS（语义不同），一并锁定 to_status 防回归
        if (Set.of("progress", "reject", "supply_info", "external_resolved").contains(action))
            assertEquals("IN_PROGRESS", captured.getValue().getToStatus());
    }

    /**
     * 工程师“接单”（claim，从 ASSIGNED 起）与员工“验收通过”（TICKET_APPROVE_ACCEPTANCE）
     * 是不同动作，事件编码必须区分：TICKET_ACCEPT。
     */
    @Test
    void engineerAcceptanceHasDistinctEventFromEmployeeAcceptance() {
        ticket(TicketStatus.ASSIGNED);
        AcceptRequest request = new AcceptRequest();
        request.setImpactScope("SINGLE");
        request.setUrgencyLevel("MEDIUM");
        service.claim(new UserContext.CurrentUser("ENG01", "Engineer", "ENGINEER", "IT"), "TK01", request);
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(captured.capture());
        assertEquals("TICKET_ACCEPT", captured.getValue().getEvent());
    }

    /**
     * 系统自动动作的事件编码：
     * 验收超时自动通过 -> TICKET_AUTO_ACCEPT；补充材料超时自动关闭 -> TICKET_AUTO_CLOSE。
     * 前端时间线依赖这两个编码区分“人操作”还是“系统操作”。
     */
    @Test
    void automaticAcceptanceAndClosureHaveExplicitEvents() {
        SlaAutoTransitionService auto = new SlaAutoTransitionService(tickets, flows, mock(WorkCalendarService.class),
                sla, notifications, mock(ExceptionQueueService.class));
        auto.autoAccept(ticket(TicketStatus.PENDING_ACCEPTANCE));
        auto.supplementTimeoutClose(ticket(TicketStatus.PENDING_SUPPLEMENT));
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows, times(2)).insert(captured.capture());
        assertEquals("TICKET_AUTO_ACCEPT", captured.getAllValues().get(0).getEvent());
        assertEquals("TICKET_AUTO_CLOSE", captured.getAllValues().get(1).getEvent());
    }

    /**
     * 超时转派（响应 SLA 未接单，系统自动换人）：
     * 事件 = TICKET_TIMEOUT_TRANSFER，且 from/to 状态都必须保持 ASSIGNED ——
     * 这只是处理人变更，不是工单状态机的迁移，绝不允许凭空发明一个状态。
     */
    @Test
    void timeoutReassignmentRecordsItsActionWithoutInventingAStateTransition() {
        Ticket ticket = ticket(TicketStatus.ASSIGNED);
        RoutingService actual = spy(new RoutingService(mock(CategoryRouteMapper.class), mock(TeamMemberMapper.class),
                mock(AssignmentMapper.class), tickets, mock(UserClient.class), mock(WorkCalendarService.class),
                mock(ExceptionQueueService.class), notifications, flows));
        doReturn("ENG02").when(actual).selectEngineer(eq("C_NET"), anySet());
        Assignment assignment = new Assignment();
        assignment.setBizType("TICKET");
        assignment.setBizId("TK01");
        assignment.setEngineerId("ENG01");
        actual.transferOnTimeout(assignment);
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(captured.capture());
        assertEquals("TICKET_TIMEOUT_TRANSFER", captured.getValue().getEvent());
        assertEquals("ASSIGNED", captured.getValue().getFromStatus());
        assertEquals("ASSIGNED", captured.getValue().getToStatus());
    }
}
