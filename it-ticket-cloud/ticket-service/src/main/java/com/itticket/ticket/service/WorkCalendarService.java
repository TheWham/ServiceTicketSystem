package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.ticket.entity.WorkCalendar;
import com.itticket.ticket.mapper.WorkCalendarMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;

/**
 * 服务日历工时引擎 —— PRD §11.1。
 * 默认周一~五 09:00-18:00 为工作时间；work_calendar 表可覆盖节假日/特殊日。
 * 提供：工作秒累计（时间区间内的有效工作秒）、工作截止时间推算（起算点+工作秒）。
 * 午餐不暂停（lunch_pause=0 为默认值，午休仍计工作）。
 */
@Service
@RequiredArgsConstructor
public class WorkCalendarService {

    private final WorkCalendarMapper workCalendarMapper;

    private static final LocalTime DEFAULT_START = LocalTime.of(9, 0);
    private static final LocalTime DEFAULT_END = LocalTime.of(18, 0);

    /** 某日是否工作日 */
    public boolean isWorkday(LocalDate date) {
        WorkCalendar cal = workCalendarMapper.selectOne(
                new QueryWrapper<WorkCalendar>().eq("cal_date", date).last("limit 1"));
        if (cal != null) {
            return "WORKDAY".equals(cal.getDayType());
        }
        DayOfWeek dow = date.getDayOfWeek();
        return dow != DayOfWeek.SATURDAY && dow != DayOfWeek.SUNDAY;
    }

    /** 某日工作时段 [start, end]；非工作日返回 null */
    public LocalTime[] workWindow(LocalDate date) {
        if (!isWorkday(date)) return null;
        WorkCalendar cal = workCalendarMapper.selectOne(
                new QueryWrapper<WorkCalendar>().eq("cal_date", date).last("limit 1"));
        LocalTime start = (cal != null && cal.getStartTime() != null) ? cal.getStartTime() : DEFAULT_START;
        LocalTime end = (cal != null && cal.getEndTime() != null) ? cal.getEndTime() : DEFAULT_END;
        return new LocalTime[]{start, end};
    }

    /**
     * 计算 [from, to] 之间的有效工作秒（跨工作日逐段累加，跳非工作时间与节假日）。
     * 若 from >= to 返回 0。
     */
    public long workSecondsBetween(LocalDateTime from, LocalDateTime to) {
        if (from == null || to == null || !to.isAfter(from)) return 0;
        long total = 0;
        LocalDate date = from.toLocalDate();
        LocalDate endDate = to.toLocalDate();
        while (!date.isAfter(endDate)) {
            LocalTime[] w = workWindow(date);
            if (w != null) {
                LocalDateTime dayStart = LocalDateTime.of(date, w[0]);
                LocalDateTime dayEnd = LocalDateTime.of(date, w[1]);
                LocalDateTime segStart = from.isAfter(dayStart) ? from : dayStart;
                LocalDateTime segEnd = to.isBefore(dayEnd) ? to : dayEnd;
                if (segEnd.isAfter(segStart)) {
                    total += java.time.Duration.between(segStart, segEnd).getSeconds();
                }
            }
            date = date.plusDays(1);
        }
        return total;
    }

    /**
     * 从起算点开始，累加 workSeconds 个工作秒后的截止时间。
     * 用于：响应截止（10 工作分钟）、SLA 目标截止推算。
     */
    public LocalDateTime addWorkSeconds(LocalDateTime from, long workSeconds) {
        if (from == null) return null;
        LocalDateTime cursor = from;
        long remaining = workSeconds;
        int guard = 0;
        while (remaining > 0 && guard++ < 3660) {
            LocalDate date = cursor.toLocalDate();
            LocalTime[] w = workWindow(date);
            if (w == null) {
                // 非工作日：跳到次日 00:00 再处理
                cursor = LocalDateTime.of(date.plusDays(1), LocalTime.MIDNIGHT);
                continue;
            }
            LocalDateTime dayStart = LocalDateTime.of(date, w[0]);
            LocalDateTime dayEnd = LocalDateTime.of(date, w[1]);
            if (cursor.isBefore(dayStart)) cursor = dayStart;
            if (!cursor.isBefore(dayEnd)) {
                // 当天已下班：跳到次日
                cursor = LocalDateTime.of(date.plusDays(1), LocalTime.MIDNIGHT);
                continue;
            }
            long availToday = java.time.Duration.between(cursor, dayEnd).getSeconds();
            if (availToday >= remaining) {
                return cursor.plusSeconds(remaining);
            }
            remaining -= availToday;
            cursor = LocalDateTime.of(date.plusDays(1), LocalTime.MIDNIGHT);
        }
        return cursor;
    }

    /** 当前是否工作时间（供扫描器判断是否该推进计时，可选优化） */
    public boolean isWorkingNow() {
        LocalDateTime now = LocalDateTime.now();
        LocalTime[] w = workWindow(now.toLocalDate());
        if (w == null) return false;
        LocalTime t = now.toLocalTime();
        return !t.isBefore(w[0]) && t.isBefore(w[1]);
    }
}
