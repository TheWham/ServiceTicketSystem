package com.itticket.consultation.service;

import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import org.assertj.core.api.ThrowableAssert.ThrowingCallable;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 服务日历与响应 SLA 工作时间计算(AX-002 / AX-008)。
 *
 * <p>契约来源:
 * <ul>
 *   <li>PRD 11.1 服务日历:周一至周五 09:00-18:00,法定节假日由管理员维护,非工作时间不消耗 SLA;</li>
 *   <li>PRD 11.2 响应 SLA:人工咨询 10 个工作分钟(600 秒),对应 AC-03「10 个工作分钟响应计时」;</li>
 *   <li>PRD 11.3:第 8 个工作分钟(480 秒)提醒;</li>
 *   <li>AX-002:工作时段重叠或逆序的日历配置拒绝发布,返回 SLA_CONFIG_INVALID;</li>
 *   <li>AX-008:必须覆盖跨午休、跨夜、跨周末与节假日/调休向量。</li>
 * </ul>
 *
 * <p>注意时间口径(DM-001):WorkCalendar 的入参与出参都是 <b>UTC 挂钟时间</b>的 LocalDateTime,
 * 而工作日与工作时段按日历时区 Asia/Shanghai 判定,北京时间 = UTC + 8。
 * 测试里统一用 {@link #utc(int, int, int, int, int)} 把北京时间换算成 UTC 入参,避免手工加减 8 小时出错。
 */
class WorkCalendarTest {

    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");

    /** PRD 11.2:人工咨询响应目标 10 个工作分钟。 */
    private static final long RESPONSE_TARGET_SECONDS = 600L;

    /** 与 db/init/31-consultation-seed.sql 的 work_intervals_json 保持一致。 */
    private static final List<WorkCalendar.WorkInterval> INTERVALS = List.of(
            new WorkCalendar.WorkInterval(LocalTime.of(9, 0), LocalTime.of(12, 0)),
            new WorkCalendar.WorkInterval(LocalTime.of(13, 0), LocalTime.of(18, 0)));

    // 测试基准周:2026-03-02 周一 ~ 2026-03-08 周日,2026-03-09 为下周一
    private static final LocalDate MONDAY = LocalDate.of(2026, 3, 2);
    private static final LocalDate TUESDAY = LocalDate.of(2026, 3, 3);
    private static final LocalDate FRIDAY = LocalDate.of(2026, 3, 6);
    private static final LocalDate SATURDAY = LocalDate.of(2026, 3, 7);
    private static final LocalDate SUNDAY = LocalDate.of(2026, 3, 8);
    private static final LocalDate NEXT_MONDAY = LocalDate.of(2026, 3, 9);
    private static final LocalDate NEXT_TUESDAY = LocalDate.of(2026, 3, 10);

    private static WorkCalendar calendar() {
        return calendar(Map.of());
    }

    private static WorkCalendar calendar(Map<LocalDate, Boolean> dayOverrides) {
        return new WorkCalendar("DEFAULT", 1L, ZONE,
                EnumSet.of(DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                        DayOfWeek.THURSDAY, DayOfWeek.FRIDAY),
                INTERVALS, dayOverrides);
    }

    /** 北京时间 -> UTC 挂钟时间(WorkCalendar 的入参/出参口径)。 */
    private static LocalDateTime utc(int year, int month, int day, int hour, int minute) {
        return ZonedDateTime.of(LocalDate.of(year, month, day), LocalTime.of(hour, minute), ZONE)
                .withZoneSameInstant(ZoneOffset.UTC)
                .toLocalDateTime();
    }

    private static LocalDateTime utc(LocalDate date, int hour, int minute) {
        return utc(date.getYear(), date.getMonthValue(), date.getDayOfMonth(), hour, minute);
    }

    private static void assertSlaConfigInvalid(ThrowingCallable callable) {
        assertThatThrownBy(callable)
                .isInstanceOfSatisfying(ApiException.class,
                        ex -> assertThat(ex.getCode()).isEqualTo(ApiCode.SLA_CONFIG_INVALID));
    }

    // ------------------------------------------------------------------
    // 零、测试基准日期自检(防止向量本身写错星期)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-08 测试基准日期自检:2026-03-02 是周一,03-06 周五,03-07/08 周末")
    void f08_fixture_dates_have_expected_day_of_week() {
        assertThat(MONDAY.getDayOfWeek()).isEqualTo(DayOfWeek.MONDAY);
        assertThat(TUESDAY.getDayOfWeek()).isEqualTo(DayOfWeek.TUESDAY);
        assertThat(FRIDAY.getDayOfWeek()).isEqualTo(DayOfWeek.FRIDAY);
        assertThat(SATURDAY.getDayOfWeek()).isEqualTo(DayOfWeek.SATURDAY);
        assertThat(SUNDAY.getDayOfWeek()).isEqualTo(DayOfWeek.SUNDAY);
        assertThat(NEXT_MONDAY.getDayOfWeek()).isEqualTo(DayOfWeek.MONDAY);
        assertThat(NEXT_TUESDAY.getDayOfWeek()).isEqualTo(DayOfWeek.TUESDAY);
        // 北京时间 10:00 对应 UTC 02:00
        assertThat(utc(MONDAY, 10, 0)).isEqualTo(LocalDateTime.of(2026, 3, 2, 2, 0));
    }

    @Test
    @DisplayName("F-08 日历元数据:calendarId 与 version 原样返回,供 SLA 实例快照引用")
    void f08_calendar_metadata_is_exposed() {
        WorkCalendar calendar = calendar();

        assertThat(calendar.calendarId()).isEqualTo("DEFAULT");
        assertThat(calendar.version()).isEqualTo(1L);
    }

    // ------------------------------------------------------------------
    // 一、deadlineUtc:10 个工作分钟响应截止时刻(AC-03)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-03 工作时段内起算 10 个工作分钟:周一 10:00 -> 周一 10:10(北京时间)")
    void ac03_deadline_inside_working_hours() {
        LocalDateTime deadline =
                calendar().deadlineUtc(utc(MONDAY, 10, 0), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(MONDAY, 10, 10));
    }

    @Test
    @DisplayName("AC-03 跨午休:周一 11:55 起算 10 个工作分钟 -> 周一 13:05(午休不消耗 SLA)")
    void ac03_deadline_skips_lunch_break() {
        LocalDateTime deadline =
                calendar().deadlineUtc(utc(MONDAY, 11, 55), RESPONSE_TARGET_SECONDS);

        // 11:55-12:00 消耗 5 分钟,12:00-13:00 午休不计,剩余 5 分钟落在 13:00-13:05
        assertThat(deadline).isEqualTo(utc(MONDAY, 13, 5));
    }

    @Test
    @DisplayName("AC-03 恰好用尽上午时段:周一 11:50 起算 10 个工作分钟 -> 周一 12:00 边界")
    void ac03_deadline_lands_exactly_on_morning_boundary() {
        LocalDateTime deadline =
                calendar().deadlineUtc(utc(MONDAY, 11, 50), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(MONDAY, 12, 0));
    }

    @Test
    @DisplayName("AC-03 跨夜:周一 17:55 起算 10 个工作分钟 -> 次工作日 09:05")
    void ac03_deadline_rolls_over_to_next_working_day() {
        LocalDateTime deadline =
                calendar().deadlineUtc(utc(MONDAY, 17, 55), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(TUESDAY, 9, 5));
    }

    @Test
    @DisplayName("AC-03 跨周末(AX-008 指定向量):周五 17:55 起算 10 个工作分钟 -> 下周一 09:05")
    void ac03_deadline_crosses_weekend() {
        LocalDateTime deadline =
                calendar().deadlineUtc(utc(FRIDAY, 17, 55), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(NEXT_MONDAY, 9, 5));
    }

    @Test
    @DisplayName("AC-03 非工作时间起算:周六上午 10:00 -> 下周一 09:10(非工作时间不消耗 SLA)")
    void ac03_deadline_starts_at_next_opening_when_outside_working_hours() {
        LocalDateTime deadline =
                calendar().deadlineUtc(utc(SATURDAY, 10, 0), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(NEXT_MONDAY, 9, 10));
    }

    @Test
    @DisplayName("AC-03 午休中起算:周一 12:30 -> 周一 13:10")
    void ac03_deadline_starts_at_afternoon_when_inside_lunch_break() {
        LocalDateTime deadline =
                calendar().deadlineUtc(utc(MONDAY, 12, 30), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(MONDAY, 13, 10));
    }

    @Test
    @DisplayName("F-08 PRD 11.3 临期提醒:周一 09:00 起算 480 秒 -> 周一 09:08")
    void f08_near_breach_reminder_deadline() {
        LocalDateTime deadline = calendar().deadlineUtc(utc(MONDAY, 9, 0), 480L);

        assertThat(deadline).isEqualTo(utc(MONDAY, 9, 8));
    }

    @Test
    @DisplayName("F-08 整日目标:周一 09:00 起算 8 个工作小时 -> 周一 18:00")
    void f08_deadline_consumes_whole_working_day() {
        LocalDateTime deadline = calendar().deadlineUtc(utc(MONDAY, 9, 0), 8 * 3600L);

        assertThat(deadline).isEqualTo(utc(MONDAY, 18, 0));
    }

    // ------------------------------------------------------------------
    // 二、节假日与调休(PRD 11.1 法定节假日由平台管理员维护)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-08 法定假日覆盖:下周一被标记为休息日,周五 17:55 的截止顺延到下周二 09:05")
    void f08_deadline_skips_statutory_holiday() {
        WorkCalendar calendar = calendar(Map.of(NEXT_MONDAY, Boolean.FALSE));

        LocalDateTime deadline = calendar.deadlineUtc(utc(FRIDAY, 17, 55), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(NEXT_TUESDAY, 9, 5));
    }

    @Test
    @DisplayName("F-08 调休补班覆盖:周六被标记为工作日,周五 17:55 的截止落在周六 09:05")
    void f08_deadline_counts_makeup_working_day() {
        WorkCalendar calendar = calendar(Map.of(SATURDAY, Boolean.TRUE));

        LocalDateTime deadline = calendar.deadlineUtc(utc(FRIDAY, 17, 55), RESPONSE_TARGET_SECONDS);

        assertThat(deadline).isEqualTo(utc(SATURDAY, 9, 5));
    }

    @Test
    @DisplayName("F-08 isWorkingDay:工作周按周几判定,dayOverrides 双向覆盖")
    void f08_is_working_day_honours_overrides() {
        WorkCalendar plain = calendar();
        assertThat(plain.isWorkingDay(MONDAY)).isTrue();
        assertThat(plain.isWorkingDay(FRIDAY)).isTrue();
        assertThat(plain.isWorkingDay(SATURDAY)).isFalse();
        assertThat(plain.isWorkingDay(SUNDAY)).isFalse();

        WorkCalendar overridden = calendar(Map.of(
                NEXT_MONDAY, Boolean.FALSE,   // 法定假日
                SATURDAY, Boolean.TRUE));     // 调休补班
        assertThat(overridden.isWorkingDay(NEXT_MONDAY)).isFalse();
        assertThat(overridden.isWorkingDay(SATURDAY)).isTrue();
        assertThat(overridden.isWorkingDay(SUNDAY)).isFalse();
        assertThat(overridden.isWorkingDay(MONDAY)).isTrue();
    }

    @Test
    @DisplayName("F-08 调休补班同样计入已用工作秒:周五 17:00 到周六 10:00 = 2 个工作小时")
    void f08_elapsed_counts_makeup_working_day() {
        WorkCalendar calendar = calendar(Map.of(SATURDAY, Boolean.TRUE));

        long elapsed = calendar.elapsedWorkSeconds(utc(FRIDAY, 17, 0), utc(SATURDAY, 10, 0));

        assertThat(elapsed).isEqualTo(2 * 3600L);
    }

    // ------------------------------------------------------------------
    // 三、elapsedWorkSeconds:已消耗工作秒(AX-002)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-03 跨午休:周一 11:00 到 14:00 只累计 2 个工作小时")
    void ac03_elapsed_excludes_lunch_break() {
        long elapsed = calendar().elapsedWorkSeconds(utc(MONDAY, 11, 0), utc(MONDAY, 14, 0));

        assertThat(elapsed).isEqualTo(2 * 3600L);
    }

    @Test
    @DisplayName("AC-03 跨夜:周一 17:00 到周二 10:00 只累计 2 个工作小时")
    void ac03_elapsed_excludes_off_hours() {
        long elapsed = calendar().elapsedWorkSeconds(utc(MONDAY, 17, 0), utc(TUESDAY, 10, 0));

        assertThat(elapsed).isEqualTo(2 * 3600L);
    }

    @Test
    @DisplayName("AC-03 跨周末:周五 17:00 到下周一 10:00 只累计 2 个工作小时")
    void ac03_elapsed_excludes_weekend() {
        long elapsed = calendar().elapsedWorkSeconds(utc(FRIDAY, 17, 0), utc(NEXT_MONDAY, 10, 0));

        assertThat(elapsed).isEqualTo(2 * 3600L);
    }

    @Test
    @DisplayName("F-08 完整工作日:周一 09:00 到 18:00 = 8 个工作小时(扣除 1 小时午休)")
    void f08_elapsed_full_working_day() {
        long elapsed = calendar().elapsedWorkSeconds(utc(MONDAY, 9, 0), utc(MONDAY, 18, 0));

        assertThat(elapsed).isEqualTo(8 * 3600L);
    }

    @Test
    @DisplayName("F-08 完全落在非工作时间的区间不消耗 SLA:周六 09:00 到周日 18:00 = 0")
    void f08_elapsed_is_zero_across_weekend_only() {
        long elapsed = calendar().elapsedWorkSeconds(utc(SATURDAY, 9, 0), utc(SUNDAY, 18, 0));

        assertThat(elapsed).isZero();
    }

    @Test
    @DisplayName("F-08 完全落在午休内的区间不消耗 SLA:周一 12:10 到 12:50 = 0")
    void f08_elapsed_is_zero_inside_lunch_break() {
        long elapsed = calendar().elapsedWorkSeconds(utc(MONDAY, 12, 10), utc(MONDAY, 12, 50));

        assertThat(elapsed).isZero();
    }

    @Test
    @DisplayName("F-08 end 早于/等于 start 或入参为 null 时返回 0,不产生负数工作秒")
    void f08_elapsed_is_zero_for_invalid_range() {
        WorkCalendar calendar = calendar();

        assertThat(calendar.elapsedWorkSeconds(utc(MONDAY, 14, 0), utc(MONDAY, 11, 0))).isZero();
        assertThat(calendar.elapsedWorkSeconds(utc(MONDAY, 14, 0), utc(MONDAY, 14, 0))).isZero();
        assertThat(calendar.elapsedWorkSeconds(null, utc(MONDAY, 14, 0))).isZero();
        assertThat(calendar.elapsedWorkSeconds(utc(MONDAY, 14, 0), null)).isZero();
        assertThat(calendar.elapsedWorkSeconds(null, null)).isZero();
    }

    @Test
    @DisplayName("AC-03 deadlineUtc 与 elapsedWorkSeconds 互为逆运算:截止时刻恰好消耗 600 工作秒")
    void ac03_deadline_and_elapsed_are_consistent() {
        WorkCalendar calendar = calendar();

        // 工作时段内起算
        LocalDateTime insideStart = utc(MONDAY, 11, 55);
        assertThat(calendar.elapsedWorkSeconds(
                insideStart, calendar.deadlineUtc(insideStart, RESPONSE_TARGET_SECONDS)))
                .isEqualTo(RESPONSE_TARGET_SECONDS);

        // 非工作时间起算(跨周末)
        LocalDateTime outsideStart = utc(SATURDAY, 10, 0);
        assertThat(calendar.elapsedWorkSeconds(
                outsideStart, calendar.deadlineUtc(outsideStart, RESPONSE_TARGET_SECONDS)))
                .isEqualTo(RESPONSE_TARGET_SECONDS);
    }

    // ------------------------------------------------------------------
    // 四、非法配置(AX-002 -> SLA_CONFIG_INVALID)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("F-08 工作时段逆序拒绝发布:SLA_CONFIG_INVALID")
    void f08_reversed_interval_is_rejected() {
        assertSlaConfigInvalid(() -> new WorkCalendar("BAD", 1L, ZONE,
                EnumSet.of(DayOfWeek.MONDAY),
                List.of(new WorkCalendar.WorkInterval(LocalTime.of(18, 0), LocalTime.of(9, 0))),
                Map.of()));
    }

    @Test
    @DisplayName("F-08 工作时段起止相同(零长度)拒绝发布:SLA_CONFIG_INVALID")
    void f08_zero_length_interval_is_rejected() {
        assertSlaConfigInvalid(() -> new WorkCalendar("BAD", 1L, ZONE,
                EnumSet.of(DayOfWeek.MONDAY),
                List.of(new WorkCalendar.WorkInterval(LocalTime.of(9, 0), LocalTime.of(9, 0))),
                Map.of()));
    }

    @Test
    @DisplayName("F-08 工作时段重叠拒绝发布:SLA_CONFIG_INVALID")
    void f08_overlapping_intervals_are_rejected() {
        assertSlaConfigInvalid(() -> new WorkCalendar("BAD", 1L, ZONE,
                EnumSet.of(DayOfWeek.MONDAY),
                List.of(new WorkCalendar.WorkInterval(LocalTime.of(9, 0), LocalTime.of(13, 0)),
                        new WorkCalendar.WorkInterval(LocalTime.of(12, 0), LocalTime.of(18, 0))),
                Map.of()));
    }

    @Test
    @DisplayName("F-08 未配置任何工作时段拒绝发布:SLA_CONFIG_INVALID")
    void f08_empty_intervals_are_rejected() {
        assertSlaConfigInvalid(() -> new WorkCalendar("BAD", 1L, ZONE,
                EnumSet.of(DayOfWeek.MONDAY), List.of(), Map.of()));
    }

    @Test
    @DisplayName("F-08 SLA 目标非正数拒绝计算:SLA_CONFIG_INVALID")
    void f08_non_positive_target_is_rejected() {
        WorkCalendar calendar = calendar();

        assertSlaConfigInvalid(() -> calendar.deadlineUtc(utc(MONDAY, 10, 0), 0L));
        assertSlaConfigInvalid(() -> calendar.deadlineUtc(utc(MONDAY, 10, 0), -1L));
    }

    @Test
    @DisplayName("F-08 无任何工作日时 deadlineUtc 在推进上限内失败而非死循环:SLA_CONFIG_INVALID")
    void f08_calendar_without_working_day_fails_fast() {
        WorkCalendar calendar = new WorkCalendar("NONE", 1L, ZONE,
                EnumSet.noneOf(DayOfWeek.class), INTERVALS, Map.of());

        assertSlaConfigInvalid(() -> calendar.deadlineUtc(utc(MONDAY, 10, 0), RESPONSE_TARGET_SECONDS));
    }
}
