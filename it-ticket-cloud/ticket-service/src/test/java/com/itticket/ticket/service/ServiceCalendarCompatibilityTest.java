package com.itticket.ticket.service;
import org.junit.jupiter.api.Test;
import java.time.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class ServiceCalendarCompatibilityTest {
 private ServiceWorkCalendar calendar(Map<LocalDate,Boolean> holidays) {
  return new ServiceWorkCalendar("DEFAULT",1L,ZoneId.of("Asia/Shanghai"),EnumSet.range(DayOfWeek.MONDAY,DayOfWeek.FRIDAY),
   List.of(new ServiceWorkCalendar.WorkInterval(LocalTime.of(9,0),LocalTime.of(12,0)),new ServiceWorkCalendar.WorkInterval(LocalTime.of(13,0),LocalTime.of(18,0))),holidays);
 }
 @Test void utcDeadlineUsesShanghaiBusinessDayAndLunchIntervals() {
  var calendar=calendar(Map.of());
  var start=LocalDateTime.of(2026,9,29,3,55); // 11:55 Shanghai
  assertEquals(LocalDateTime.of(2026,9,29,5,5),calendar.deadlineUtc(start,600));
  assertEquals(600L,calendar.elapsedWorkSeconds(start,LocalDateTime.of(2026,9,29,5,5)));
 }
 @Test void holidayAndWeekendOverridesApplyInCalendarTimezone() {
  var calendar=calendar(Map.of(LocalDate.of(2026,10,1),false,LocalDate.of(2026,10,3),true));
  assertFalse(calendar.isWorkingDay(LocalDate.of(2026,10,1)));
  assertTrue(calendar.isWorkingDay(LocalDate.of(2026,10,3)));
 }
}
