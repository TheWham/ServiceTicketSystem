package com.itticket.ticket.service;

import com.itticket.ticket.entity.SlaInstance;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.mapper.SlaInstanceMapper;
import com.itticket.ticket.mapper.SlaPauseMapper;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.provider.ValueSource;
import java.time.LocalDateTime;
import java.util.List;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class SlaWithdrawalRaceTest {
    @Test void activeTicketStillGetsItsOverdueSlaProcessed() {
        SlaInstanceMapper slas = mock(SlaInstanceMapper.class);
        TicketMapper tickets = mock(TicketMapper.class);
        WorkCalendarService calendar = mock(WorkCalendarService.class);
        NotificationService notifications = mock(NotificationService.class);
        ExceptionQueueService exceptions = mock(ExceptionQueueService.class);
        SlaService service = new SlaService(slas, mock(SlaPauseMapper.class), tickets, calendar, notifications, exceptions);
        SlaInstance current = new SlaInstance(); current.setSlaId("SLA1"); current.setBizId("TK01");
        current.setTicketId("TK01"); current.setStatus("RUNNING"); current.setCreatedAt(LocalDateTime.now().minusDays(2));
        current.setTargetAt(LocalDateTime.now().minusDays(1)); current.setPrioritySnapshot("MEDIUM");
        when(slas.selectList(any())).thenReturn(List.of(current));
        when(slas.selectOne(any())).thenReturn(current);
        Ticket active = new Ticket(); active.setTicketId("TK01"); active.setStatus(TicketStatus.IN_PROGRESS);
        active.setAssigneeId("ENG01"); active.setTitle("Active");
        when(tickets.selectOne(any())).thenReturn(active);
        when(tickets.selectById("TK01")).thenReturn(active);
        service.scan();
        org.mockito.ArgumentCaptor<SlaInstance> updated = org.mockito.ArgumentCaptor.forClass(SlaInstance.class);
        verify(slas).updateById(updated.capture());
        org.junit.jupiter.api.Assertions.assertEquals("BREACHED", updated.getValue().getStatus());
        verify(notifications).sendInbox(eq("SLA_BREACHED:TK01"), eq("ENG01"), anyString(), anyString(), anyString());
    }

    @ParameterizedTest
    @ValueSource(booleans = {false, true})
    void staleRunningSnapshotDoesNotRestartCancelledSlaOrNotifyEngineer(boolean overdue) {
        SlaInstanceMapper slas = mock(SlaInstanceMapper.class);
        TicketMapper tickets = mock(TicketMapper.class);
        WorkCalendarService calendar = mock(WorkCalendarService.class);
        NotificationService notifications = mock(NotificationService.class);
        ExceptionQueueService exceptions = mock(ExceptionQueueService.class);
        SlaService service = new SlaService(slas, mock(SlaPauseMapper.class), tickets, calendar, notifications, exceptions);
        SlaInstance snapshot = new SlaInstance();
        snapshot.setSlaId("SLA1"); snapshot.setBizId("TK01"); snapshot.setBizType("TICKET");
        snapshot.setTicketId("TK01");
        snapshot.setStatus("RUNNING"); snapshot.setCreatedAt(LocalDateTime.now().minusDays(1));
        snapshot.setTargetAt(overdue ? LocalDateTime.now().minusDays(1) : LocalDateTime.now().plusDays(1));
        snapshot.setTargetWorkSeconds(100L); snapshot.setPrioritySnapshot("MEDIUM");
        when(slas.selectList(any())).thenReturn(List.of(snapshot));
        when(calendar.workSecondsBetween(any(), any())).thenReturn(90L);
        Ticket cancelled = new Ticket(); cancelled.setTicketId("TK01"); cancelled.setStatus(TicketStatus.CANCELLED);
        cancelled.setAssigneeId("ENG01"); cancelled.setTitle("Archived");
        when(tickets.selectById("TK01")).thenReturn(cancelled);
        when(tickets.selectOne(any())).thenReturn(cancelled);
        service.scan();
        verify(slas, never()).updateById(any(SlaInstance.class));
        verify(slas, never()).update(any(), any());
        verifyNoInteractions(notifications, exceptions);
    }
}
