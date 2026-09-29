package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.entity.CalendarHoliday;
import com.itticket.consultation.entity.ServiceCalendarRow;
import com.itticket.consultation.mapper.CalendarHolidayMapper;
import com.itticket.consultation.mapper.ServiceCalendarRowMapper;
import com.itticket.consultation.support.Json;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 服务日历装载(AX-002)。
 *
 * <p>日历是可重建的配置投影,按 DM-006 允许缓存;此处用进程内缓存 + 版本号,
 * 管理员更新日历后版本变化即失效。日历不可用时回退到 PRD 11.1 的默认值,
 * 并记录告警 —— 不得因为配置缺失而阻塞转人工(RD-013)。
 *
 * <p>默认时区取 Asia/Shanghai:AX-005 把"服务日历时区、午休默认和节假日数据源"列为未决项,
 * 这里给出一期默认值,平台确认后改为配置下发。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ServiceCalendarProvider {

    private static final ZoneId DEFAULT_ZONE = ZoneId.of("Asia/Shanghai");
    private static final Set<DayOfWeek> DEFAULT_WORK_DAYS = EnumSet.of(
            DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY);
    private static final List<WorkCalendar.WorkInterval> DEFAULT_INTERVALS =
            List.of(new WorkCalendar.WorkInterval(LocalTime.of(9, 0), LocalTime.of(18, 0)));

    private final ServiceCalendarRowMapper calendarMapper;
    private final CalendarHolidayMapper holidayMapper;
    private final ConsultationProperties properties;

    private volatile CachedCalendar cache;

    public WorkCalendar current() {
        String calendarId = properties.getSla().getCalendarId();
        ServiceCalendarRow row = calendarMapper.selectById(calendarId);
        if (row == null) {
            log.warn("[sla] 服务日历 {} 不存在,使用 PRD 11.1 默认日历", calendarId);
            return defaultCalendar(calendarId);
        }
        CachedCalendar cached = cache;
        long version = row.getVersion() == null ? 0L : row.getVersion();
        if (cached != null && cached.calendarId().equals(calendarId) && cached.version() == version) {
            return cached.calendar();
        }
        WorkCalendar calendar = build(row, version);
        cache = new CachedCalendar(calendarId, version, calendar);
        return calendar;
    }

    private WorkCalendar build(ServiceCalendarRow row, long version) {
        ZoneId zone;
        try {
            zone = ZoneId.of(row.getTimezone());
        } catch (RuntimeException e) {
            log.warn("[sla] 服务日历 {} 时区非法: {},回退默认时区", row.getCalendarId(), row.getTimezone());
            zone = DEFAULT_ZONE;
        }

        Set<DayOfWeek> workDays = parseWorkDays(row.getWorkWeekJson());
        List<WorkCalendar.WorkInterval> intervals = parseIntervals(row.getWorkIntervalsJson());
        Map<LocalDate, Boolean> overrides = loadOverrides(row.getCalendarId());
        return new WorkCalendar(row.getCalendarId(), version, zone, workDays, intervals, overrides);
    }

    private WorkCalendar defaultCalendar(String calendarId) {
        return new WorkCalendar(calendarId, 0L, DEFAULT_ZONE, DEFAULT_WORK_DAYS, DEFAULT_INTERVALS, Map.of());
    }

    private Set<DayOfWeek> parseWorkDays(String json) {
        List<?> raw = Json.read(json, List.class);
        if (raw == null || raw.isEmpty()) {
            return DEFAULT_WORK_DAYS;
        }
        Set<DayOfWeek> days = EnumSet.noneOf(DayOfWeek.class);
        for (Object value : raw) {
            days.add(DayOfWeek.of(((Number) value).intValue()));
        }
        return days;
    }

    @SuppressWarnings("unchecked")
    private List<WorkCalendar.WorkInterval> parseIntervals(String json) {
        List<Map<String, Object>> raw = Json.read(json, List.class);
        if (raw == null || raw.isEmpty()) {
            return DEFAULT_INTERVALS;
        }
        List<WorkCalendar.WorkInterval> intervals = new ArrayList<>(raw.size());
        for (Map<String, Object> entry : raw) {
            intervals.add(new WorkCalendar.WorkInterval(
                    LocalTime.parse(String.valueOf(entry.get("start"))),
                    LocalTime.parse(String.valueOf(entry.get("end")))));
        }
        return intervals;
    }

    private Map<LocalDate, Boolean> loadOverrides(String calendarId) {
        List<CalendarHoliday> holidays = holidayMapper.selectList(Wrappers.<CalendarHoliday>lambdaQuery()
                .eq(CalendarHoliday::getCalendarId, calendarId));
        Map<LocalDate, Boolean> overrides = new HashMap<>(holidays.size());
        for (CalendarHoliday holiday : holidays) {
            overrides.put(holiday.getHolidayDate(),
                    Boolean.TRUE.equals(holiday.getIsWorkingDay()));
        }
        return overrides;
    }

    private record CachedCalendar(String calendarId, long version, WorkCalendar calendar) {
    }
}
