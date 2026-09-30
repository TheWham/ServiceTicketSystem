package com.itticket.ticket.service;

import com.itticket.ticket.entity.Notification;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.mapper.NotificationMapper;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.DuplicateKeyException;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * 通知投递的降级兜底（PRD §14.3）：
 * - dedup_key 唯一键冲突 → 幂等跳过，不重发不入异常队列
 * - 工单标题查询失败 → 降级为单号，通知照常投递
 * - 数据库级故障（非唯一键）→ 异常抛给 @Async 边界，由异步线程隔离，不拖垮业务主流程
 */
class NotificationDegradationTest {

    private NotificationMapper notificationMapper;
    private ExceptionQueueService exceptionQueue;
    private TicketMapper ticketMapper;
    private NotificationService service;

    @BeforeEach
    void setUp() {
        notificationMapper = mock(NotificationMapper.class);
        exceptionQueue = mock(ExceptionQueueService.class);
        ticketMapper = mock(TicketMapper.class);
        service = new NotificationService(notificationMapper, exceptionQueue, ticketMapper);
    }

    private Ticket ticket(String id, String title) {
        Ticket t = new Ticket();
        t.setTicketId(id);
        t.setTitle(title);
        return t;
    }

    /** 同一事件重复触发（重试/重放）→ 幂等占位冲突即跳过：不更新状态、不入异常队列 */
    @Test
    void duplicateDedupKeySkipsDeliverySilently() {
        when(ticketMapper.selectById("TK01")).thenReturn(ticket("TK01", "打印机故障"));
        doThrow(new DuplicateKeyException("Duplicate entry 'ASSIGNED:TK01:U1:IN_APP'"))
                .when(notificationMapper).insert(any(Notification.class));

        assertDoesNotThrow(() -> service.sendNotification("TK01", "ASSIGNED", "U1"));

        verify(notificationMapper, never()).updateById(any(Notification.class));
        verifyNoInteractions(exceptionQueue);
    }

    /** 工单表查询异常 → 标题降级为单号，通知仍然落库投递 */
    @Test
    void titleLookupFailureDegradesToTicketId() {
        when(ticketMapper.selectById("TK02")).thenThrow(new DataAccessResourceFailureException("DB down"));

        service.sendNotification("TK02", "ASSIGNED", "ENG01");

        ArgumentCaptor<Notification> captor = ArgumentCaptor.forClass(Notification.class);
        verify(notificationMapper).insert(captor.capture());
        Notification n = captor.getValue();
        assertTrue(n.getTitle().contains("TK02"), "标题降级后应包含单号: " + n.getTitle());
        assertTrue(n.getTitle().contains("新工单待接单"));
        assertEquals("ASSIGNED:TK02:ENG01:IN_APP", n.getDedupKey());
    }

    /** 数据库非幂等故障 → 异常向 @Async 边界传播（生产上由异步线程池隔离，不阻断业务线程） */
    @Test
    void databaseFailurePropagatesToAsyncBoundary() {
        when(ticketMapper.selectById("TK03")).thenReturn(ticket("TK03", "网络不可用"));
        doThrow(new DataAccessResourceFailureException("connection reset"))
                .when(notificationMapper).insert(any(Notification.class));

        assertThrows(DataAccessResourceFailureException.class,
                () -> service.sendNotification("TK03", "SUBMIT_SUCCESS", "U_EMP01"));
    }

    /** 投递后状态更新失败 → 同样抛给异步边界，不影响已落库的通知本体 */
    @Test
    void statusUpdateFailurePropagatesToAsyncBoundary() {
        when(ticketMapper.selectById("TK04")).thenReturn(ticket("TK04", "VPN 连不上"));
        doThrow(new DataAccessResourceFailureException("lock wait timeout"))
                .when(notificationMapper).updateById(any(Notification.class));

        assertThrows(DataAccessResourceFailureException.class,
                () -> service.sendNotification("TK04", "ACCEPTED", "ENG01"));
    }
}
