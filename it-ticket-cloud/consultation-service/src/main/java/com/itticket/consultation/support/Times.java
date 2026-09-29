package com.itticket.consultation.support;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;

/**
 * 时间口径(DM-001 / DM-001.1)。
 *
 * <p>持久化层一律使用 {@link LocalDateTime} 承载 <b>UTC 挂钟时间</b> 写入 {@code DATETIME(6)}:
 * JDBC 对 LocalDateTime 不做时区换算,因此数据库会话时区、JVM 默认时区变化都不会改变已存事实。
 * 对外 JSON 一律输出 ISO 8601 带时区字符串(AI-002),由 {@link #iso(LocalDateTime)} 生成。
 * 业务时区只在服务日历计算内部出现,不泄漏到存储。
 */
public final class Times {

    private static final DateTimeFormatter ISO_UTC =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSS'Z'");

    private Times() {
    }

    /** 当前 UTC 时间,截断到微秒以匹配 DATETIME(6)。 */
    public static LocalDateTime nowUtc() {
        return LocalDateTime.now(ZoneOffset.UTC).truncatedTo(ChronoUnit.MICROS);
    }

    public static LocalDateTime fromInstant(Instant instant) {
        return instant == null ? null
                : LocalDateTime.ofInstant(instant, ZoneOffset.UTC).truncatedTo(ChronoUnit.MICROS);
    }

    public static Instant toInstant(LocalDateTime utc) {
        return utc == null ? null : utc.toInstant(ZoneOffset.UTC);
    }

    /** 对外时间格式:ISO 8601 带时区(AI-002)。入参为 UTC 挂钟时间。 */
    public static String iso(LocalDateTime utc) {
        return utc == null ? null : ISO_UTC.format(utc);
    }
}
