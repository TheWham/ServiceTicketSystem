package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.ActionRequest;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.entity.Assignment;
import com.itticket.ticket.entity.Attachment;
import com.itticket.ticket.controller.SlaController;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.*;
import org.apache.ibatis.builder.MapperBuilderAssistant;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockito.ArgumentCaptor;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class TicketWithdrawalTest {
    private final TicketMapper tickets = mock(TicketMapper.class);
    private final TicketFlowLogMapper flows = mock(TicketFlowLogMapper.class);
    private final AttachmentMapper attachments = mock(AttachmentMapper.class);
    private final TicketPurgeMapper purge = mock(TicketPurgeMapper.class);
    private final SlaService sla = mock(SlaService.class);
    private final RoutingService routing = mock(RoutingService.class);
    private final TicketService service = new TicketService(tickets, mock(CategoryMapper.class), attachments, flows,
            purge, mock(TicketNoGenerator.class), mock(NotificationService.class), mock(UserClient.class), sla,
            routing, mock(ExceptionQueueService.class), mock(ConsultationConvertNotifier.class), new ObjectMapper());
    private final UserContext.CurrentUser owner = new UserContext.CurrentUser("EMP01", "Employee", "EMPLOYEE", "IT");
    private final UserContext.CurrentUser engineer = new UserContext.CurrentUser("ENG01", "Engineer", "ENGINEER", "IT");
    private final UserContext.CurrentUser admin = new UserContext.CurrentUser("ADMIN", "Admin", "PLATFORM_ADMIN", "IT");

    @BeforeAll static void metadata() {
        TableInfoHelper.initTableInfo(new MapperBuilderAssistant(new MybatisConfiguration(), ""), Ticket.class);
    }

    private Ticket ticket(TicketStatus status) {
        Ticket t = new Ticket();
        t.setTicketId("TK01"); t.setCreatorId("EMP01"); t.setAssigneeId("ENG01"); t.setStatus(status);
        t.setTitle("Original content");
        when(tickets.selectById("TK01")).thenReturn(t);
        when(tickets.selectOne(any())).thenReturn(t);
        when(tickets.update(isNull(), any())).thenReturn(1);
        return t;
    }

    @ParameterizedTest
    @EnumSource(value = TicketStatus.class, names = {"NEW", "ASSIGNED", "IN_PROGRESS", "PENDING_SUPPLEMENT", "PENDING_EXTERNAL", "PENDING_ACCEPTANCE"})
    @SuppressWarnings({"rawtypes", "unchecked"})
    void withdrawsActiveOwnTicketAndRetainsArchive(TicketStatus status) {
        ticket(status);
        assertEquals("CANCELLED", service.withdraw(owner, "TK01").get("status"));
        ArgumentCaptor<LambdaUpdateWrapper> update = ArgumentCaptor.forClass(LambdaUpdateWrapper.class);
        verify(tickets).update(isNull(), update.capture());
        String sql = update.getValue().getSqlSet();
        assertTrue(sql.contains("status="));
        assertTrue(sql.contains("closed_at="));
        assertFalse(sql.contains("assignee_id="));
        assertFalse(sql.contains("description="));
        assertFalse(sql.contains("created_at="));
        assertFalse(sql.contains("solved_at="));
        verify(sla).cancel("TK01");
        verify(routing).cancelAssignments("TK01");
        verifyNoInteractions(purge, attachments);
        ArgumentCaptor<TicketFlowLog> log = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(log.capture());
        assertEquals("TICKET_CANCEL", log.getValue().getEvent());
        assertEquals("CANCELLED", log.getValue().getToStatus());
        assertEquals(status.getValue(), log.getValue().getFromStatus());
    }

    @ParameterizedTest
    @EnumSource(value = TicketStatus.class, names = {"CANCELLED", "COMPLETED", "CLOSED"})
    void terminalTicketsCannotBeWithdrawnAgain(TicketStatus status) {
        ticket(status);
        assertThrows(BizException.class, () -> service.withdraw(owner, "TK01"));
        verify(tickets, never()).update(any(), any());
        verifyNoInteractions(sla, routing, flows);
    }

    @Test void cannotWithdrawForAnotherUserEvenAsAdminOrAssignedEngineer() {
        ticket(TicketStatus.ASSIGNED);
        for (var user : List.of(engineer, admin)) assertThrows(BizException.class, () -> service.withdraw(user, "TK01"));
        ActionRequest cancel = new ActionRequest(); cancel.setAction("cancel");
        assertThrows(BizException.class, () -> service.action(engineer, "TK01", cancel));
        verify(tickets, never()).update(any(), any());
    }

    @Test void withdrawnArchiveVisibleToOwnerAndAdminButNotEngineer() {
        ticket(TicketStatus.CANCELLED);
        assertThrows(BizException.class, () -> service.get(engineer, "TK01"));
        assertNotNull(service.get(owner, "TK01").get("ticket"));
        assertNotNull(service.get(admin, "TK01").get("ticket"));
    }

    @Test @SuppressWarnings({"rawtypes", "unchecked"})
    void engineerListExcludesWithdrawnBeforePaginationEvenWithExplicitStatusFilter() {
        when(tickets.selectPage(any(Page.class), any())).thenReturn(new Page<Ticket>());
        service.list(engineer, "CANCELLED", null, null, null, null, null, null, 1, 10);
        ArgumentCaptor<QueryWrapper> query = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(tickets).selectPage(any(Page.class), query.capture());
        assertTrue(query.getValue().getSqlSegment().contains("status <>"));
        assertTrue(query.getValue().getParamNameValuePairs().containsValue("CANCELLED"));
    }

    @Test @SuppressWarnings({"rawtypes", "unchecked"})
    void adminCanFilterWithdrawnArchives() {
        when(tickets.selectPage(any(Page.class), any())).thenReturn(new Page<Ticket>());
        service.list(admin, "CANCELLED", null, null, null, null, null, null, 1, 10);
        ArgumentCaptor<QueryWrapper> query = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(tickets).selectPage(any(Page.class), query.capture());
        assertFalse(query.getValue().getSqlSegment().contains("status <>"));
        assertTrue(query.getValue().getParamNameValuePairs().containsValue("CANCELLED"));
    }

    @Test void concurrentStateChangeCannotApplyStaleActionAfterWithdrawal() {
        ticket(TicketStatus.IN_PROGRESS);
        when(tickets.update(isNull(), any())).thenReturn(0);
        ActionRequest progress = new ActionRequest(); progress.setAction("progress"); progress.setRemark("Update");
        assertThrows(BizException.class, () -> service.action(engineer, "TK01", progress));
        verifyNoInteractions(sla, flows);
    }

    @Test void staleAssignmentCannotReassignWithdrawnTicket() {
        Ticket stale = ticket(TicketStatus.ASSIGNED);
        when(tickets.update(isNull(), any())).thenReturn(0);
        AssignmentMapper assignments = mock(AssignmentMapper.class);
        RoutingService actual = new RoutingService(mock(CategoryRouteMapper.class), mock(TeamMemberMapper.class),
                assignments, tickets, mock(UserClient.class), mock(WorkCalendarService.class),
                mock(ExceptionQueueService.class), mock(NotificationService.class), flows);
        assertThrows(BizException.class, () -> actual.assign(stale, "ENG02", "TRANSFERRED"));
        verifyNoInteractions(assignments, flows);
    }

    @Test void timeoutScannerIgnoresWithdrawnArchive() {
        ticket(TicketStatus.CANCELLED);
        Ticket stale = new Ticket(); stale.setTicketId("TK01"); stale.setStatus(TicketStatus.ASSIGNED);
        when(tickets.selectById("TK01")).thenReturn(stale);
        AssignmentMapper assignments = mock(AssignmentMapper.class);
        CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
        RoutingService actual = new RoutingService(routes, mock(TeamMemberMapper.class), assignments, tickets,
                mock(UserClient.class), mock(WorkCalendarService.class), mock(ExceptionQueueService.class),
                mock(NotificationService.class), flows);
        Assignment previous = new Assignment(); previous.setBizType("TICKET"); previous.setBizId("TK01"); previous.setEngineerId("ENG01");
        actual.transferOnTimeout(previous);
        verifyNoInteractions(routes, assignments, flows);
    }

    @Test void withdrawnSlaIsHiddenFromEngineerButOwnerAndAdminCanRead() {
        ticket(TicketStatus.CANCELLED);
        SlaInstanceMapper instances = mock(SlaInstanceMapper.class);
        SlaController controller = new SlaController(instances, mock(WorkCalendarService.class), tickets);
        try {
            UserContext.set(engineer);
            assertThrows(BizException.class, () -> controller.getByTicket("TK01"));
            verifyNoInteractions(instances);
            UserContext.set(owner);
            assertNotNull(controller.getByTicket("TK01"));
            UserContext.set(admin);
            assertNotNull(controller.getByTicket("TK01"));
        } finally { UserContext.clear(); }
    }

    @Test void withdrawnPhotosRemainForOwnerAndAdminOnly(@org.junit.jupiter.api.io.TempDir java.nio.file.Path dir) throws Exception {
        ticket(TicketStatus.CANCELLED);
        Attachment att = new Attachment(); att.setAttachmentId("A1"); att.setBizId("TK01");
        att.setUploaderId("EMP01"); att.setObjectKey("archive.png"); att.setFileName("archive.png"); att.setContentType("image/png");
        when(attachments.selectById("A1")).thenReturn(att);
        byte[] content = {1, 2, 3}; java.nio.file.Files.write(dir.resolve("archive.png"), content);
        AttachmentService photos = new AttachmentService(attachments, tickets);
        org.springframework.test.util.ReflectionTestUtils.setField(photos, "storageDir", dir.toString());
        assertThrows(BizException.class, () -> photos.readContent(engineer, "A1"));
        assertArrayEquals(content, photos.readContent(owner, "A1").bytes());
        assertArrayEquals(content, photos.readContent(admin, "A1").bytes());
    }
}
