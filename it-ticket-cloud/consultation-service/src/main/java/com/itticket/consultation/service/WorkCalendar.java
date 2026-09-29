package com.itticket.consultation.service;

import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;

import java.time.DayOfWeek;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 服务日历与工作时间计算(AX-002 / AX-008 伪代码的实现)。
 *
 * <p>输入输出都是 UTC 挂钟时间({@code LocalDateTime}),切片按日历时区进行,
 * 因此周末、节假日、调休和夏令时切换都按业务时区判定,再换算回 Instant 口径。
 * 咨询响应 SLA 没有合法暂停原因(SlaPauseReason 只覆盖工单等待),故本类不处理暂停区间。
 */
public final class WorkCalendar {

    /** 推进上限,防止日历配置异常导致死循环。10 个工作分钟的目标远在此界内。 */
    private static final int MAX_LOOKAHEAD_DAYS = 366;

    private final String calendarId;
    private final long version;
    private final ZoneId zone;
    private final Set<DayOfWeek> workDays;
    private final List<WorkInterval> intervals;
    /** 日期 → 是否按工作日处理。true 表示调休补班,false 表示法定休息。 */
    private final Map<LocalDate, Boolean> dayOverrides;

    public WorkCalendar(String calendarId, long version, ZoneId zone, Set<DayOfWeek> workDays,
                        List<WorkInterval> intervals, Map<LocalDate, Boolean> dayOverrides) {
        this.calendarId = calendarId;
        this.version = version;
        this.zone = zone;
        this.workDays = Set.copyOf(workDays);
        this.intervals = validate(intervals);
        this.dayOverrides = Map.copyOf(dayOverrides);
    }

    /** 工作时段。左闭右开。 */
    public record WorkInterval(LocalTime start, LocalTime end) {
    }

    /** AX-002:重叠或逆序的时段配置拒绝发布并返回 SLA_CONFIG_INVALID。 */
    private static List<WorkInterval> validate(List<WorkInterval> raw) {
        List<WorkInterval> sorted = raw.stream()
                .sorted(java.util.Comparator.comparing(WorkInterval::start))
                .toList();
        if (sorted.isEmpty()) {
            throw new ApiException(ApiCode.SLA_CONFIG_INVALID, "服务日历未配置工作时段");
        }
        LocalTime previousEnd = null;
        for (WorkInterval interval : sorted) {
            if (!interval.start().isBefore(interval.end())) {
                throw new ApiException(ApiCode.SLA_CONFIG_INVALID, "服务日历工作时段逆序: " + interval);
            }
            if (previousEnd != null && interval.start().isBefore(previousEnd)) {
                throw new ApiException(ApiCode.SLA_CONFIG_INVALID, "服务日历工作时段重叠: " + interval);
            }
            previousEnd = interval.end();
        }
        return sorted;
    }

    public String calendarId() {
        return calendarId;
    }

    public long version() {
        return version;
    }

    public boolean isWorkingDay(LocalDate date) {
        Boolean override = dayOverrides.get(date);
        if (override != null) {
            return override;
        }
        return workDays.contains(date.getDayOfWeek());
    }

    /**
     * 从 startUtc 起消耗 targetWorkSeconds 个工作秒后的截止时刻。
     * 起点落在非工作时段时,从下一个工作时段开始计时(PRD 11.1:非工作时间不消耗 SLA)。
     */
    public LocalDateTime deadlineUtc(LocalDateTime startUtc, long targetWorkSeconds) {
        if (targetWorkSeconds <= 0) {
            throw new ApiException(ApiCode.SLA_CONFIG_INVALID, "SLA 目标必须大于 0 秒");
        }
        ZonedDateTime cursor = startUtc.atOffset(ZoneOffset.UTC).atZoneSameInstant(zone);
        long remaining = targetWorkSeconds;

        LocalDate day = cursor.toLocalDate();
        for (int i = 0; i < MAX_LOOKAHEAD_DAYS; i++, day = day.plusDays(1)) {
            if (!isWorkingDay(day)) {
                continue;
            }
            for (WorkInterval interval : intervals) {
                ZonedDateTime segmentStart = ZonedDateTime.of(day, interval.start(), zone);
                ZonedDateTime segmentEnd = ZonedDateTime.of(day, interval.end(), zone);
                if (!segmentEnd.isAfter(cursor)) {
                    continue;
                }
                ZonedDateTime from = cursor.isAfter(segmentStart) ? cursor : segmentStart;
                long usable = Duration.between(from, segmentEnd).getSeconds();
                if (usable <= 0) {
                    continue;
                }
                if (usable >= remaining) {
                    return toUtc(from.plusSeconds(remaining));
                }
                remaining -= usable;
            }
        }
        throw new ApiException(ApiCode.SLA_CONFIG_INVALID, "服务日历在 " + MAX_LOOKAHEAD_DAYS + " 天内无法满足 SLA 目标");
    }

    /** startUtc 到 endUtc 之间的有效工作秒数。end 早于 start 时返回 0。 */
    public long elapsedWorkSeconds(LocalDateTime startUtc, LocalDateTime endUtc) {
        if (startUtc == null || endUtc == null || !endUtc.isAfter(startUtc)) {
            return 0L;
        }
        ZonedDateTime start = startUtc.atOffset(ZoneOffset.UTC).atZoneSameInstant(zone);
        ZonedDateTime end = endUtc.atOffset(ZoneOffset.UTC).atZoneSameInstant(zone);
        long total = 0L;

        LocalDate day = start.toLocalDate();
        for (int i = 0; i < MAX_LOOKAHEAD_DAYS && !day.isAfter(end.toLocalDate()); i++, day = day.plusDays(1)) {
            if (!isWorkingDay(day)) {
                continue;
            }
            for (WorkInterval interval : intervals) {
                ZonedDateTime segmentStart = ZonedDateTime.of(day, interval.start(), zone);
                ZonedDateTime segmentEnd = ZonedDateTime.of(day, interval.end(), zone);
                ZonedDateTime from = start.isAfter(segmentStart) ? start : segmentStart;
                ZonedDateTime to = end.isBefore(segmentEnd) ? end : segmentEnd;
                if (to.isAfter(from)) {
                    total += Duration.between(from, to).getSeconds();
                }
            }
        }
        return total;
    }

    private static LocalDateTime toUtc(ZonedDateTime zoned) {
        return zoned.withZoneSameInstant(ZoneOffset.UTC).toLocalDateTime();
    }
}
