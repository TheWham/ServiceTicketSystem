package com.itticket.ticket.service;

import com.baomidou.mybatisplus.annotation.TableField;
import com.itticket.ticket.entity.*;
import com.itticket.ticket.mapper.*;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import java.time.LocalDateTime;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/**
 * 规范持久化层回归（对齐 01-data-model-strong-types.md 与 06-mysql-ddl-and-migrations.md）：
 *  - 实体字段与规范列名必须显式映射（nature / event / breach_at / ticket_id），防止 MyBatis-Plus
 *    驼峰推断在列名不一致时静默写错列；
 *  - SLA 扫描器只能按规范维度（biz_type=TICKET + sla_type=TICKET_COMPLETION）圈定待扫描实例；
 *  - 完工时限实例启动时必须固化业务字段与日历快照（calendar_id / calendar_version）。
 */
class CanonicalPersistenceTest {

    /**
     * 列映射回归：Ticket.nature、TicketFlowLog.event、SlaInstance.breachAt/ticketId
     * 三个关键列必须保持 @TableField 显式声明 —— 这些列名与驼峰推断不一致，
     * 一旦注解丢失会造成读写错位（这类 bug 在集成环境才暴露，代价很高）。
     */
    @Test
    void canonicalColumnsAreExplicitlyMapped() throws Exception {
        assertEquals("nature", Ticket.class.getDeclaredField("nature").getAnnotation(TableField.class).value());
        assertEquals("event", TicketFlowLog.class.getDeclaredField("event").getAnnotation(TableField.class).value());
        assertEquals("breach_at", SlaInstance.class.getDeclaredField("breachAt").getAnnotation(TableField.class).value());
        assertNotNull(SlaInstance.class.getDeclaredField("ticketId"));
    }

    /**
     * SLA 到期扫描器的查询条件回归：
     * scan() 必须只圈定“工单 + 完工时限”这一组合（biz_type=TICKET, sla_type=TICKET_COMPLETION），
     * 否则咨询会话等其他业务类型的 SLA 实例会被工单扫描逻辑误处理。
     */
    @Test
    void completionScannerOnlyQueriesTicketSlaInstances() {
        SlaInstanceMapper mapper = mock(SlaInstanceMapper.class);
        when(mapper.selectList(any())).thenReturn(List.of());
        SlaService service = new SlaService(mapper, mock(SlaPauseMapper.class), mock(TicketMapper.class),
                mock(WorkCalendarService.class), mock(NotificationService.class), mock(ExceptionQueueService.class));
        service.scan();
        ArgumentCaptor<QueryWrapper<SlaInstance>> query = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(mapper).selectList(query.capture());
        assertTrue(query.getValue().getSqlSegment().contains("biz_type"));
        assertTrue(query.getValue().getParamNameValuePairs().containsValue("TICKET"));
        assertTrue(query.getValue().getParamNameValuePairs().containsValue("TICKET_COMPLETION"));
    }

    /**
     * 完工时限实例启动契约：
     *  - 业务标识三元组（TICKET / TK01 / TICKET_COMPLETION + ticket_id 回填）齐全；
     *  - MEDIUM 优先级目标工时为 8 小时 = 28800 秒；
     *  - 必须固化当日历快照（calendar_id=DEFAULT、calendar_version=1），
     *    保证日后日历调整不影响已签发实例的违约判定口径。
     */
    @Test
    void canonicalCompletionSlaHasBusinessAndCalendarFields() {
        SlaInstanceMapper mapper = mock(SlaInstanceMapper.class);
        WorkCalendarService calendar = mock(WorkCalendarService.class);
        when(calendar.calendarId()).thenReturn("DEFAULT");
        when(calendar.calendarVersion()).thenReturn(1L);
        when(calendar.addWorkSeconds(any(), anyLong())).thenAnswer(i -> ((LocalDateTime) i.getArgument(0)).plusHours(8));
        SlaService service = new SlaService(mapper, mock(SlaPauseMapper.class), mock(TicketMapper.class), calendar,
                mock(NotificationService.class), mock(ExceptionQueueService.class));
        SlaInstance sla = service.startCompletionSla("TK01", "MEDIUM", LocalDateTime.of(2026, 9, 29, 1, 0));
        assertEquals("TICKET", sla.getBizType());
        assertEquals("TK01", sla.getBizId());
        assertEquals("TICKET_COMPLETION", sla.getSlaType());
        assertEquals("TK01", sla.getTicketId());
        assertEquals(28800L, sla.getTargetWorkSeconds());
        assertEquals("DEFAULT", sla.getCalendarId());
        assertEquals(1L, sla.getCalendarVersion());
    }
}