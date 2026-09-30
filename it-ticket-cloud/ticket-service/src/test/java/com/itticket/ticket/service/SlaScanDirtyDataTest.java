package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.MybatisConfiguration;
import com.baomidou.mybatisplus.core.metadata.TableInfoHelper;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * SLA 自动化扫描对脏数据 / 局部故障的容错：
 * - 单个分支抛异常不能影响其余两个分支继续执行
 * - 工单时间戳缺失（updatedAt = null 的历史脏数据）→ 回退 createdAt
 * - 并发下条件更新 0 行 → 跳过副作用（不发通知、不停 SLA、不写流水）
 */
class SlaScanDirtyDataTest {

    private TicketMapper ticketMapper;
    private TicketFlowLogMapper flowLogMapper;
    private WorkCalendarService workCalendar;
    private SlaService slaService;
    private NotificationService notificationService;
    private ExceptionQueueService exceptionQueue;
    private SlaAutoTransitionService service;

    @BeforeEach
    void setUp() {
        // LambdaUpdateWrapper 列解析依赖 MyBatis-Plus 实体元数据缓存，纯单测需手动初始化
        TableInfoHelper.initTableInfo(
                new org.apache.ibatis.builder.MapperBuilderAssistant(new MybatisConfiguration(), ""), Ticket.class);
        ticketMapper = mock(TicketMapper.class);
        flowLogMapper = mock(TicketFlowLogMapper.class);
        workCalendar = mock(WorkCalendarService.class);
        slaService = mock(SlaService.class);
        notificationService = mock(NotificationService.class);
        exceptionQueue = mock(ExceptionQueueService.class);
        service = new SlaAutoTransitionService(ticketMapper, flowLogMapper, workCalendar,
                slaService, notificationService, exceptionQueue);
    }

    /** scan() 三个分支按固定顺序各查一次：1=自动验收(模拟抛错) 2=逾期补充(脏工单) 3=外部等待(空) */
    private void stubDispatch(Ticket supplementTicket) {
        java.util.concurrent.atomic.AtomicInteger calls = new java.util.concurrent.atomic.AtomicInteger();
        when(ticketMapper.selectList(any())).thenAnswer(inv -> {
            int n = calls.incrementAndGet();
            if (n == 1) {
                throw new RuntimeException("simulated DB hiccup");
            }
            if (n == 2) {
                return supplementTicket == null ? List.of() : List.of(supplementTicket);
            }
            return List.of();
        });
    }

    /** 自动验收分支 DB 抖动 → 异常被 scan() 吸收，逾期补充分支照常关闭工单 */
    @Test
    void oneBranchFailureDoesNotStopSiblingScans() {
        Ticket dirty = new Ticket();
        dirty.setTicketId("TK_DIRTY");
        dirty.setStatus(TicketStatus.PENDING_SUPPLEMENT);
        dirty.setUpdatedAt(null); // 历史脏数据：无更新时间
        dirty.setCreatedAt(LocalDateTime.now(ZoneOffset.UTC).minusDays(100));
        dirty.setCreatorId(null); // 脏数据：无创建人
        dirty.setAssigneeId("ENG01");
        stubDispatch(dirty);
        LocalDateTime past = LocalDateTime.now(ZoneOffset.UTC).minusHours(1);
        when(workCalendar.addWorkSeconds(any(), anyLong())).thenReturn(past);
        when(ticketMapper.update(isNull(), any())).thenReturn(1);

        assertDoesNotThrow(() -> service.scan());

        // 逾期补充分支：updatedAt 为 null 时用 createdAt 起算
        ArgumentCaptor<LocalDateTime> base = ArgumentCaptor.forClass(LocalDateTime.class);
        verify(workCalendar).addWorkSeconds(base.capture(), eq(72L * 3600));
        assertEquals(dirty.getCreatedAt(), base.getValue());
        // 工单被关闭 + 流水落库
        verify(flowLogMapper).insert(any(TicketFlowLog.class));
        verify(slaService).cancel("TK_DIRTY");
        // 创建人为脏 null → 只通知工程师一次
        verify(notificationService, times(1)).sendNotification("TK_DIRTY", "SUPPLEMENT_TIMEOUT_CLOSED", "ENG01");
    }

    /** 并发场景：PENDING_ACCEPTANCE 已被别的实例处理掉（条件更新 0 行）→ 全部副作用跳过 */
    @Test
    void concurrentAutoAcceptSkipsAllSideEffects() {
        Ticket t = new Ticket();
        t.setTicketId("TK_RACE");
        t.setStatus(TicketStatus.PENDING_ACCEPTANCE);
        t.setCreatorId("U_EMP01");
        when(ticketMapper.update(isNull(), any())).thenReturn(0);

        service.autoAccept(t);

        verifyNoInteractions(slaService, flowLogMapper, notificationService);
    }

    /** 外部等待新工单（未超时）→ 不入异常队列 */
    @Test
    void externalWaitWithinDeadlineNotRaised() {
        Ticket t = new Ticket();
        t.setTicketId("TK_EXT");
        t.setStatus(TicketStatus.PENDING_EXTERNAL);
        t.setUpdatedAt(LocalDateTime.now(ZoneOffset.UTC));
        when(ticketMapper.selectList(any())).thenReturn(List.of(t));
        when(workCalendar.addWorkSeconds(any(), anyLong()))
                .thenReturn(LocalDateTime.now(ZoneOffset.UTC).plusDays(3));

        service.scanExternalWaitTimeout();

        verifyNoInteractions(exceptionQueue);
    }

    /** 外部等待超时且无 updatedAt 的脏工单 → 正常入异常队列（不自动改状态） */
    @Test
    void externalWaitTimeoutWithMissingTimestampsRaisesQueue() {
        Ticket t = new Ticket();
        t.setTicketId("TK_EXT2");
        t.setStatus(TicketStatus.PENDING_EXTERNAL);
        t.setUpdatedAt(null);
        t.setCreatedAt(LocalDateTime.now(ZoneOffset.UTC).minusDays(30));
        t.setPriority("HIGH");
        when(ticketMapper.selectList(any())).thenReturn(List.of(t));
        when(workCalendar.addWorkSeconds(any(), anyLong()))
                .thenReturn(LocalDateTime.now(ZoneOffset.UTC).minusMinutes(1));

        service.scanExternalWaitTimeout();

        verify(exceptionQueue).raise(eq("TICKET"), eq("TK_EXT2"),
                eq(ExceptionQueueService.TYPE_LONG_PENDING), any(), any(), eq("HIGH"));
        // 不自动流转：不更新工单、不写流水
        verify(ticketMapper, never()).update(isNull(), any());
        verifyNoInteractions(flowLogMapper);
    }
}
