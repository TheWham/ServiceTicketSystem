package com.itticket.common.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;
import java.time.LocalDateTime;
import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Jackson 时间序列化契约测试（common-web.JacksonTimeConfig）。
 *
 * 全系统时间约定：
 *   - 数据库存 UTC 时间（MySQL TIMESTAMP 按 UTC 存取）；
 *   - 后端响应统一输出带 Z（UTC 偏移）的 ISO-8601 字符串，前端按浏览器时区自行转换显示；
 *   - 反序列化兼容两种入参格式：
 *       a) 带偏移的 ISO-8601（新客户端），归一化为 UTC；
 *       b) "yyyy-MM-dd HH:mm:ss" 遗留格式（无偏移），按服务声明时区（本项目 +08:00）解释后转 UTC。
 */
class JacksonTimeConfigTest {

    /** 构造应用了 JacksonTimeConfig 定制器的 ObjectMapper（与 Spring 容器中的配置等价） */
    private ObjectMapper mapper() {
        Jackson2ObjectMapperBuilder builder = new Jackson2ObjectMapperBuilder();
        new JacksonTimeConfig().localDateTimeCustomizer().customize(builder);
        return builder.build();
    }

    /** DB 中的 UTC LocalDateTime 序列化必须带 Z 后缀，前端不会误当本地时间 */
    @Test
    void utcDatabaseTimeIncludesOffsetInResponse() throws Exception {
        assertEquals("\"2026-09-29T01:00:00Z\"", mapper().writeValueAsString(LocalDateTime.of(2026, 9, 29, 1, 0)));
    }

    /** 客户端提交 +08:00 偏移的 09:00，应归一化为同一时刻的 UTC 01:00 */
    @Test
    void offsetInputIsNormalizedToUtc() throws Exception {
        assertEquals(LocalDateTime.of(2026, 9, 29, 1, 0),
                mapper().readValue("\"2026-09-29T09:00:00+08:00\"", LocalDateTime.class));
    }

    /** 无偏移的遗留格式按服务声明时区 +08:00 解释：09:00(+08:00) == 01:00(UTC) */
    @Test
    void legacyLocalInputUsesDeclaredServiceTimezone() throws Exception {
        assertEquals(LocalDateTime.of(2026, 9, 29, 1, 0),
                mapper().readValue("\"2026-09-29 09:00:00\"", LocalDateTime.class));
    }
}