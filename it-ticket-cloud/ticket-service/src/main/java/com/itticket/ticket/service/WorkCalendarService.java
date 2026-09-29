package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.ticket.entity.CalendarHoliday;
import com.itticket.ticket.entity.ServiceCalendarRow;
import com.itticket.ticket.mapper.CalendarHolidayMapper;
import com.itticket.ticket.mapper.ServiceCalendarRowMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.time.*;
import java.util.*;

/** Canonical service_calendar/calendar_holiday reader. Inputs and outputs are UTC. */
@Service
@RequiredArgsConstructor
public class WorkCalendarService {
    private final ServiceCalendarRowMapper calendarMapper;
    private final CalendarHolidayMapper holidayMapper;
    private final ObjectMapper objectMapper;

    public ServiceWorkCalendar current() {
        ServiceCalendarRow row = calendarMapper.selectById("DEFAULT");
        if (row == null) return new ServiceWorkCalendar("DEFAULT", 0L, ZoneId.of("Asia/Shanghai"),
                EnumSet.range(DayOfWeek.MONDAY, DayOfWeek.FRIDAY),
                List.of(new ServiceWorkCalendar.WorkInterval(LocalTime.of(9,0), LocalTime.of(18,0))), Map.of());
        try {
            Set<DayOfWeek> weekdays = EnumSet.noneOf(DayOfWeek.class);
            for (var value : objectMapper.readTree(row.getWorkWeekJson())) weekdays.add(DayOfWeek.of(value.asInt()));
            List<ServiceWorkCalendar.WorkInterval> intervals = new ArrayList<>();
            for (var value : objectMapper.readTree(row.getWorkIntervalsJson())) intervals.add(new ServiceWorkCalendar.WorkInterval(
                    LocalTime.parse(value.get("start").asText()), LocalTime.parse(value.get("end").asText())));
            Map<LocalDate, Boolean> overrides = new HashMap<>();
            for (CalendarHoliday holiday : holidayMapper.selectList(new QueryWrapper<CalendarHoliday>().eq("calendar_id",row.getCalendarId())))
                overrides.put(holiday.getHolidayDate(), Boolean.TRUE.equals(holiday.getIsWorkingDay()));
            return new ServiceWorkCalendar(row.getCalendarId(), row.getVersion() == null ? 0L : row.getVersion(),
                    ZoneId.of(row.getTimezone()), weekdays, intervals, overrides);
        } catch (Exception ex) {
            throw new BizException(ErrorCode.PARAM_INVALID, "Invalid service calendar");
        }
    }
    public String calendarId() { return current().calendarId(); }
    public long calendarVersion() { return current().version(); }
    public boolean isWorkday(LocalDate day) { return current().isWorkingDay(day); }
    public long workSecondsBetween(LocalDateTime from, LocalDateTime to) { return current().elapsedWorkSeconds(from,to); }
    public LocalDateTime addWorkSeconds(LocalDateTime from, long seconds) {
        if (from == null || seconds <= 0) return from;
        return current().deadlineUtc(from, seconds);
    }
    public boolean isWorkingNow() {
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        return workSecondsBetween(now,now.plusSeconds(1)) == 1;
    }
}
