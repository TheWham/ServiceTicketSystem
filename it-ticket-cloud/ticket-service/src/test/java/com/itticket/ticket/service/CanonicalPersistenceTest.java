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
class CanonicalPersistenceTest {
 @Test void canonicalColumnsAreExplicitlyMapped() throws Exception {
  assertEquals("ticket_nature", Ticket.class.getDeclaredField("nature").getAnnotation(TableField.class).value());
  assertEquals("event_code", TicketFlowLog.class.getDeclaredField("event").getAnnotation(TableField.class).value());
  assertEquals("breached_at", SlaInstance.class.getDeclaredField("breachAt").getAnnotation(TableField.class).value());
 }
 @Test void completionScannerOnlyQueriesTicketSlaInstances() {
  SlaInstanceMapper mapper=mock(SlaInstanceMapper.class);
  when(mapper.selectList(any())).thenReturn(List.of());
  SlaService service=new SlaService(mapper,mock(SlaPauseMapper.class),mock(TicketMapper.class),mock(WorkCalendarService.class),mock(NotificationService.class),mock(ExceptionQueueService.class));
  service.scan();
  ArgumentCaptor<QueryWrapper<SlaInstance>> query=ArgumentCaptor.forClass(QueryWrapper.class);
  verify(mapper).selectList(query.capture());
  assertTrue(query.getValue().getSqlSegment().contains("biz_type"));
  assertTrue(query.getValue().getParamNameValuePairs().containsValue("TICKET"));
  assertTrue(query.getValue().getParamNameValuePairs().containsValue("TICKET_COMPLETION"));
 }
 @Test void canonicalCompletionSlaHasBusinessAndCalendarFields() {
  SlaInstanceMapper mapper=mock(SlaInstanceMapper.class); WorkCalendarService calendar=mock(WorkCalendarService.class);
  when(calendar.calendarId()).thenReturn("DEFAULT"); when(calendar.calendarVersion()).thenReturn(1L);
  when(calendar.addWorkSeconds(any(),anyLong())).thenAnswer(i -> ((LocalDateTime)i.getArgument(0)).plusHours(8));
  SlaService service=new SlaService(mapper,mock(SlaPauseMapper.class),mock(TicketMapper.class),calendar,mock(NotificationService.class),mock(ExceptionQueueService.class));
  SlaInstance sla=service.startCompletionSla("TK01","MEDIUM",LocalDateTime.of(2026,9,29,1,0));
  assertEquals("TICKET",sla.getBizType()); assertEquals("TK01",sla.getBizId()); assertEquals("TICKET_COMPLETION",sla.getSlaType());
  assertEquals(28800L,sla.getTargetWorkSeconds()); assertEquals("DEFAULT",sla.getCalendarId()); assertEquals(1L,sla.getCalendarVersion());
 }
}
