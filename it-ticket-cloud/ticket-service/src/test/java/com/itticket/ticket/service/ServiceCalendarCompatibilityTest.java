package com.itticket.ticket.service;

import org.junit.jupiter.api.Test;
import java.time.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 工作日历计算（ServiceWorkCalendar）的行为契约：
 *  - 所有对外计算以 UTC 时间戳为准（DB 层语义），业务时段/节假日按日历所在时区（Asia/Shanghai）解释；
 *  - 工作时段为 09:00-12:00、13:00-18:00（午休不计入工时）；
 *  - 节假日表既能把工作日改为休息（如国庆），也能把周末调为上班（调休）。
 * SLA 到期与超时扫描全部依赖这一计算口径，任何偏差都会直接篡改超时判定。
 */
class ServiceCalendarCompatibilityTest {

    /**
     * 构造默认日历：周一至周五，上海时区，上午 9-12 点 + 下午 13-18 点两段工时，
     * holidays 覆盖表：key 为日期，value=false 表示该日休息、true 表示该日上班（覆盖周末规则）。
     */
    private ServiceWorkCalendar calendar(Map<LocalDate, Boolean> holidays) {
        return new ServiceWorkCalendar("DEFAULT", 1L, ZoneId.of("Asia/Shanghai"),
                EnumSet.range(DayOfWeek.MONDAY, DayOfWeek.FRIDAY),
                List.of(new ServiceWorkCalendar.WorkInterval(LocalTime.of(9, 0), LocalTime.of(12, 0)),
                        new ServiceWorkCalendar.WorkInterval(LocalTime.of(13, 0), LocalTime.of(18, 0))),
                holidays);
    }

    /**
     * 跨午休的工时累加：
     * 起点 2026-09-29 03:55 UTC = 上海 11:55，要求 +600 工时秒。
     * 11:55->12:00 消耗 300 秒后午休暂停，13:00 起再消耗 300 秒 -> 13:05 上海时间 = 05:05 UTC。
     * elapsedWorkSeconds 反向校验：起止之间的工时恰为 600 秒。
     */
    @Test
    void utcDeadlineUsesShanghaiBusinessDayAndLunchIntervals() {
        var calendar = calendar(Map.of());
        var start = LocalDateTime.of(2026, 9, 29, 3, 55); // 11:55 Shanghai
        assertEquals(LocalDateTime.of(2026, 9, 29, 5, 5), calendar.deadlineUtc(start, 600));
        assertEquals(600L, calendar.elapsedWorkSeconds(start, LocalDateTime.of(2026, 9, 29, 5, 5)));
    }

    /**
     * 节假日覆盖表双向生效（均按日历时区日期解释）：
     *  2026-10-01（周四，原工作日）标记为休息 -> isWorkingDay=false（国庆节）；
     *  2026-10-03（周六，原休息日）标记为上班 -> isWorkingDay=true（调休补班）。
     */
    @Test
    void holidayAndWeekendOverridesApplyInCalendarTimezone() {
        var calendar = calendar(Map.of(LocalDate.of(2026, 10, 1), false, LocalDate.of(2026, 10, 3), true));
        assertFalse(calendar.isWorkingDay(LocalDate.of(2026, 10, 1)));
        assertTrue(calendar.isWorkingDay(LocalDate.of(2026, 10, 3)));
    }
}