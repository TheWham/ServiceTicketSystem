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

class TicketActionEventTest {
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
            flows, mock(TicketNoGenerator.class), notifications, mock(UserClient.class), sla, routing,
            mock(ExceptionQueueService.class), mock(ConsultationConvertNotifier.class), new ObjectMapper());

    private Ticket ticket(TicketStatus status) {
        Ticket ticket = new Ticket(); ticket.setTicketId("TK01"); ticket.setStatus(status);
        ticket.setCreatorId("EMP01"); ticket.setAssigneeId("ENG01"); ticket.setPriority("MEDIUM");
        ticket.setCategoryId("C_NET");
        when(tickets.selectById("TK01")).thenReturn(ticket);
        when(tickets.update(isNull(), any())).thenReturn(1);
        when(flows.selectCount(any())).thenReturn(1L);
        return ticket;
    }

    @ParameterizedTest
    @CsvSource({
        "progress,IN_PROGRESS,TICKET_PROGRESS",
        "reject,PENDING_ACCEPTANCE,TICKET_REJECT_ACCEPTANCE",
        "supply_info,PENDING_SUPPLEMENT,TICKET_SUBMIT_SUPPLEMENT",
        "external_resolved,PENDING_EXTERNAL,TICKET_RESUME_EXTERNAL",
        "need_info,IN_PROGRESS,TICKET_REQUEST_SUPPLEMENT",
        "external,IN_PROGRESS,TICKET_START_EXTERNAL_WAIT",
        "done,IN_PROGRESS,TICKET_SUBMIT_RESOLUTION",
        "accept,PENDING_ACCEPTANCE,TICKET_APPROVE_ACCEPTANCE",
        "cancel,NEW,TICKET_CANCEL"
    })
    void actionWritesItsOwnEventEvenWhenTargetStateIsShared(String action, TicketStatus from, String event) {
        ticket(from);
        ActionRequest request = new ActionRequest(); request.setAction(action); request.setRemark("Sufficient detail for this action");
        boolean employeeAction = Set.of("reject", "supply_info", "accept", "cancel").contains(action);
        UserContext.CurrentUser user = new UserContext.CurrentUser(employeeAction ? "EMP01" : "ENG01", "User", employeeAction ? "EMPLOYEE" : "ENGINEER", "IT");
        service.action(user, "TK01", request);
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(captured.capture());
        assertEquals(event, captured.getValue().getEvent());
        assertEquals(from.getValue(), captured.getValue().getFromStatus());
        if (Set.of("progress", "reject", "supply_info", "external_resolved").contains(action))
            assertEquals("IN_PROGRESS", captured.getValue().getToStatus());
    }

    @Test void engineerAcceptanceHasDistinctEventFromEmployeeAcceptance() {
        ticket(TicketStatus.ASSIGNED);
        AcceptRequest request = new AcceptRequest(); request.setImpactScope("SINGLE"); request.setUrgencyLevel("MEDIUM");
        service.claim(new UserContext.CurrentUser("ENG01", "Engineer", "ENGINEER", "IT"), "TK01", request);
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(captured.capture());
        assertEquals("TICKET_ACCEPT", captured.getValue().getEvent());
    }

    @Test void automaticAcceptanceAndClosureHaveExplicitEvents() {
        SlaAutoTransitionService auto = new SlaAutoTransitionService(tickets, flows, mock(WorkCalendarService.class),
                sla, notifications, mock(ExceptionQueueService.class));
        auto.autoAccept(ticket(TicketStatus.PENDING_ACCEPTANCE));
        auto.supplementTimeoutClose(ticket(TicketStatus.PENDING_SUPPLEMENT));
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows, times(2)).insert(captured.capture());
        assertEquals("TICKET_AUTO_ACCEPT", captured.getAllValues().get(0).getEvent());
        assertEquals("TICKET_AUTO_CLOSE", captured.getAllValues().get(1).getEvent());
    }

    @Test void timeoutReassignmentRecordsItsActionWithoutInventingAStateTransition() {
        Ticket ticket = ticket(TicketStatus.ASSIGNED);
        RoutingService actual = spy(new RoutingService(mock(CategoryRouteMapper.class), mock(TeamMemberMapper.class),
                mock(AssignmentMapper.class), tickets, mock(UserClient.class), mock(WorkCalendarService.class),
                mock(ExceptionQueueService.class), notifications, flows));
        doReturn("ENG02").when(actual).selectEngineer(eq("C_NET"), anySet());
        Assignment assignment = new Assignment(); assignment.setBizType("TICKET"); assignment.setBizId("TK01"); assignment.setEngineerId("ENG01");
        actual.transferOnTimeout(assignment);
        ArgumentCaptor<TicketFlowLog> captured = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(captured.capture());
        assertEquals("TICKET_TIMEOUT_TRANSFER", captured.getValue().getEvent());
        assertEquals("ASSIGNED", captured.getValue().getFromStatus());
        assertEquals("ASSIGNED", captured.getValue().getToStatus());
    }
}
