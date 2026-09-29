package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.dto.TicketProjection;
import com.itticket.ticket.entity.Category;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.*;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class TicketMergeIntegrationTest {
    private final TicketMapper tickets = mock(TicketMapper.class);
    private final CategoryMapper categories = mock(CategoryMapper.class);
    private final TicketFlowLogMapper flows = mock(TicketFlowLogMapper.class);
    private final TicketNoGenerator numbers = mock(TicketNoGenerator.class);
    private final NotificationService notifications = mock(NotificationService.class);
    private final ConsultationConvertNotifier conversions = mock(ConsultationConvertNotifier.class);
    private final SlaService sla = mock(SlaService.class);
    private final RoutingService routing = mock(RoutingService.class);
    private final UserContext.CurrentUser employee = new UserContext.CurrentUser("U_EMP01", "Employee", "EMPLOYEE", "IT");
    private final ObjectMapper json = new ObjectMapper();
    private TicketService service;

    @BeforeEach void setUp() {
        com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                new org.apache.ibatis.builder.MapperBuilderAssistant(new com.baomidou.mybatisplus.core.MybatisConfiguration(), ""), Ticket.class);
        service = new TicketService(tickets, categories, mock(AttachmentMapper.class), flows, numbers,
                notifications, mock(UserClient.class), sla, routing, mock(ExceptionQueueService.class), conversions, json);
        Category leaf = new Category();
        leaf.setCategoryId("C_NET"); leaf.setName("Network"); leaf.setStatus("ACTIVE");
        when(categories.selectById("C_NET")).thenReturn(leaf);
        when(categories.selectCount(any())).thenReturn(0L);
        when(numbers.generate()).thenReturn("TK001");
        TransactionSynchronizationManager.initSynchronization();
    }
    @AfterEach void cleanUp() { TransactionSynchronizationManager.clearSynchronization(); }

    private CreateTicketRequest request() {
        CreateTicketRequest req = new CreateTicketRequest();
        req.setNature("INCIDENT"); req.setCategoryId("C_NET"); req.setTitle("Network unavailable");
        req.setDescription("The office network is unavailable.");
        req.setImpactDescription("Office network"); req.setUrgencyDescription("Cannot work");
        req.setSourceSessionId("CS001"); req.setFieldValues(Map.of("ai_summary", "Connection failed"));
        return req;
    }

    @Test void consultationCreateRetainsMainRoutingAndSlaAndContext() throws Exception {
        var outcome = service.create(employee, request(), "key-1");
        var captor = ArgumentCaptor.forClass(Ticket.class);
        verify(tickets).insert(captor.capture());
        Ticket saved = captor.getValue();
        assertEquals(TicketStatus.NEW, saved.getStatus());
        assertEquals("MEDIUM", saved.getPriority());
        assertEquals("INCIDENT", saved.getNature());
        assertEquals("CS001", saved.getSourceSessionId());
        assertEquals("key-1", saved.getIdempotencyKey());
        assertEquals("Network", saved.getCategorySnapshot());
        assertEquals("Connection failed", json.readTree(saved.getFieldSnapshotJson()).get("ai_summary").asText());
        assertNull(saved.getFirstResponseAt());
        assertFalse(outcome.duplicated());
        when(tickets.selectById("TK001")).thenReturn(saved);
        when(routing.route(saved)).thenReturn("ENG01");
        verifyNoInteractions(conversions, routing);
        verify(sla).startCompletionSla(eq("TK001"), eq("MEDIUM"), any());
        TransactionSynchronizationManager.getSynchronizations().forEach(s -> s.afterCommit());
        verify(conversions).notifyConverted("CS001", "TK001", employee);
        verify(routing).route(saved);
        var flowCaptor = ArgumentCaptor.forClass(com.itticket.ticket.entity.TicketFlowLog.class);
        verify(flows, times(2)).insert(flowCaptor.capture());
        assertEquals("TICKET_CREATE", flowCaptor.getAllValues().get(0).getEvent());
        assertEquals("TICKET_ASSIGN", flowCaptor.getAllValues().get(1).getEvent());
    }

    @Test void idempotentRetryReplaysConversionWithoutNewTicketOrRouting() {
        Ticket existing = new Ticket(); existing.setTicketId("TK001"); existing.setSourceSessionId("CS001");
        when(tickets.selectOne(any(QueryWrapper.class))).thenReturn(existing);
        assertTrue(service.create(employee, request(), "key-1").duplicated());
        verify(tickets, never()).insert(any(Ticket.class));
        verifyNoInteractions(flows, notifications, sla, routing);
        TransactionSynchronizationManager.getSynchronizations().forEach(s -> s.afterCommit());
        verify(conversions).notifyConverted("CS001", "TK001", employee);
    }

    @Test void conflictingHeaderAndBodyKeysAreRejected() {
        CreateTicketRequest req = request(); req.setIdempotencyKey("body-key");
        assertThrows(BizException.class, () -> service.create(employee, req, "header-key"));
        verify(tickets, never()).insert(any(Ticket.class));
    }

    @Test void acceptsBothNatureContractsAndPreservesUppercaseProjection() throws Exception {
        assertEquals("INCIDENT", json.readValue("{\"ticket_nature\":\"INCIDENT\"}", CreateTicketRequest.class).getNature());
        assertEquals("SERVICE_REQUEST", json.readValue("{\"nature\":\"SERVICE_REQUEST\"}", CreateTicketRequest.class).getNature());
        Ticket ticket = new Ticket(); ticket.setStatus(TicketStatus.ASSIGNED); ticket.setPriority("HIGH");
        assertEquals("HIGH", TicketProjection.of(ticket).priority());
        assertEquals("ASSIGNED", TicketProjection.of(ticket).status());
    }
}
