package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.EditTicketRequest;
import com.itticket.ticket.entity.Attachment;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.*;
import com.itticket.ticket.vo.TicketVO;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockito.ArgumentCaptor;
import java.util.List;
import java.util.Set;
import java.time.LocalDateTime;
import java.util.stream.Collectors;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class TicketEditTest {
    private final TicketMapper tickets = mock(TicketMapper.class);
    private final AttachmentMapper attachments = mock(AttachmentMapper.class);
    private final TicketFlowLogMapper flows = mock(TicketFlowLogMapper.class);
    private final SlaService sla = mock(SlaService.class);
    private final RoutingService routing = mock(RoutingService.class);
    private final TicketNoGenerator numbers = mock(TicketNoGenerator.class);
    private final TicketService service = new TicketService(tickets, mock(CategoryMapper.class), attachments,
            flows, mock(TicketPurgeMapper.class), numbers, mock(NotificationService.class),
            mock(UserClient.class), sla, routing, mock(ExceptionQueueService.class),
            mock(ConsultationConvertNotifier.class), new ObjectMapper());
    private final UserContext.CurrentUser owner = new UserContext.CurrentUser("EMP01", "Employee", "EMPLOYEE", "IT");

    private Ticket ticket(TicketStatus status) {
        Ticket ticket = new Ticket();
        ticket.setTicketId("TK01");
        ticket.setCreatorId("EMP01");
        ticket.setNature("INCIDENT");
        ticket.setCategoryId("NET");
        ticket.setCategorySnapshot("办公网络/网络连接");
        ticket.setStatus(status);
        ticket.setUpdatedAt(LocalDateTime.of(2026, 10, 1, 8, 0));
        when(tickets.selectOne(any())).thenReturn(ticket);
        when(tickets.update(isNull(), any())).thenReturn(1);
        return ticket;
    }

    private EditTicketRequest request() {
        EditTicketRequest req = new EditTicketRequest();
        req.setNature("INCIDENT");
        req.setCategoryId("NET");
        req.setTitle(" Updated title ");
        req.setDescription(" Updated details ");
        req.setImpactDescription(" One employee ");
        req.setUrgencyDescription(" Today ");
        req.setLocation("");
        req.setAttachments(List.of());
        return req;
    }

    @ParameterizedTest
    @EnumSource(value = TicketStatus.class, names = "CANCELLED", mode = EnumSource.Mode.EXCLUDE)
    @SuppressWarnings({"rawtypes", "unchecked"})
    void editOnlyWritesContentAndPreservesLifecycleAndTimers(TicketStatus status) {
        ticket(status);
        service.edit(owner, "TK01", request());
        ArgumentCaptor<UpdateWrapper> update = ArgumentCaptor.forClass(UpdateWrapper.class);
        verify(tickets).update(isNull(), update.capture());
        Set<String> columns = java.util.Arrays.stream(update.getValue().getSqlSet().split(","))
                .map(part -> part.split("=")[0]).collect(Collectors.toSet());
        assertEquals(Set.of("title", "description", "impact_description", "urgency_description",
                "location", "contact", "asset_id", "updated_at"), columns);
        assertTrue(update.getValue().getParamNameValuePairs().containsValue("Updated title"));
        assertTrue(update.getValue().getParamNameValuePairs().containsValue(null));
        // Legacy pending-state deadlines use updated_at, so content edits must preserve it too.
        assertTrue(update.getValue().getParamNameValuePairs().containsValue(LocalDateTime.of(2026, 10, 1, 8, 0)));
        verifyNoInteractions(sla, routing, numbers);
        ArgumentCaptor<TicketFlowLog> log = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flows).insert(log.capture());
        assertEquals("TICKET_EDIT", log.getValue().getEvent());
        assertEquals(status.getValue(), log.getValue().getFromStatus());
        assertEquals(status.getValue(), log.getValue().getToStatus());
    }

    @Test
    void withdrawnArchiveCannotBeEdited() {
        ticket(TicketStatus.CANCELLED);
        assertThrows(BizException.class, () -> service.edit(owner, "TK01", request()));
        verify(tickets, never()).update(any(), any());
    }

    @Test
    void rejectsAnotherCreatorWithoutWriting() {
        ticket(TicketStatus.NEW);
        assertThrows(BizException.class, () -> service.edit(
                new UserContext.CurrentUser("OTHER", "Other", "PLATFORM_ADMIN", "IT"), "TK01", request()));
        verify(tickets, never()).update(any(), any());
        verifyNoInteractions(attachments, flows, sla);
    }

    @Test
    void rejectsChangedCategoryOrNature() {
        ticket(TicketStatus.NEW);
        EditTicketRequest req = request();
        req.setCategoryId("OTHER");
        assertThrows(BizException.class, () -> service.edit(owner, "TK01", req));
        req.setCategoryId("NET");
        req.setNature("SERVICE_REQUEST");
        assertThrows(BizException.class, () -> service.edit(owner, "TK01", req));
        verify(tickets, never()).update(any(), any());
    }

    @Test
    void rejectsBlankContentAndTooManyAttachments() {
        ticket(TicketStatus.NEW);
        EditTicketRequest req = request();
        req.setDescription(" ");
        assertThrows(BizException.class, () -> service.edit(owner, "TK01", req));
        req.setDescription("Details");
        req.setAttachments(List.of("A", "B", "C", "D"));
        assertThrows(BizException.class, () -> service.edit(owner, "TK01", req));
        verify(tickets, never()).update(any(), any());
    }

    @Test
    void rejectsForeignOrUnavailableAttachmentsBeforeWriting() {
        ticket(TicketStatus.NEW);
        EditTicketRequest req = request();
        req.setAttachments(List.of("OTHER"));
        Attachment foreign = new Attachment();
        foreign.setAttachmentId("OTHER");
        foreign.setUploaderId("OTHER");
        foreign.setBizId("OTHER");
        foreign.setBizType("TICKET");
        foreign.setScanStatus("PASSED");
        when(attachments.selectById("OTHER")).thenReturn(foreign);
        assertThrows(BizException.class, () -> service.edit(owner, "TK01", req));
        verify(tickets, never()).update(any(), any());
    }

    @Test
    @SuppressWarnings({"rawtypes", "unchecked"})
    void reuploadingWithdrawnPhotoReusesItsTicketHashInsteadOfViolatingUniqueKey() {
        ticket(TicketStatus.IN_PROGRESS);
        Attachment uploaded = new Attachment();
        uploaded.setAttachmentId("NEW");
        uploaded.setBizType("TICKET");
        uploaded.setBizId("EMP01");
        uploaded.setUploaderId("EMP01");
        uploaded.setScanStatus("PASSED");
        uploaded.setHash("same-image-hash");
        Attachment previous = new Attachment();
        previous.setAttachmentId("OLD");
        previous.setBizType("TICKET");
        previous.setBizId("TK01");
        previous.setUploaderId("EMP01");
        previous.setScanStatus("PASSED");
        previous.setHash("same-image-hash");
        previous.setWithdrawnAt(LocalDateTime.of(2026, 10, 2, 8, 0));
        when(attachments.selectById("NEW")).thenReturn(uploaded);
        when(attachments.selectOne(any())).thenReturn(previous);
        when(attachments.update(isNull(), any())).thenReturn(1);
        EditTicketRequest req = request();
        req.setAttachments(List.of("NEW"));
        service.edit(owner, "TK01", req);
        ArgumentCaptor<UpdateWrapper> writes = ArgumentCaptor.forClass(UpdateWrapper.class);
        verify(attachments, atLeastOnce()).update(isNull(), writes.capture());
        assertTrue(writes.getAllValues().stream().noneMatch(w -> w.getSqlSet().contains("biz_id=")),
                "Existing hash must never be bound under a second attachment ID");
        assertTrue(writes.getAllValues().stream().anyMatch(w ->
                w.getSqlSet().contains("withdrawn_at=") && w.getParamNameValuePairs().containsValue(null)));
    }

    @Test
    void detailExposesCategorySnapshotEvenWhenCategoryIsNoLongerActive() throws Exception {
        Ticket t = ticket(TicketStatus.NEW);
        String json = new ObjectMapper().findAndRegisterModules().writeValueAsString(TicketVO.from(t));
        assertEquals("办公网络/网络连接", new ObjectMapper().readTree(json).path("category_name").asText());
    }
}
