package com.itticket.common.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;
import java.time.LocalDateTime;
import static org.junit.jupiter.api.Assertions.assertEquals;

class JacksonTimeConfigTest {
    private ObjectMapper mapper() {
        Jackson2ObjectMapperBuilder builder = new Jackson2ObjectMapperBuilder();
        new JacksonTimeConfig().localDateTimeCustomizer().customize(builder);
        return builder.build();
    }

    @Test
    void utcDatabaseTimeIncludesOffsetInResponse() throws Exception {
        assertEquals("\"2026-09-29T01:00:00Z\"", mapper().writeValueAsString(LocalDateTime.of(2026, 9, 29, 1, 0)));
    }

    @Test
    void offsetInputIsNormalizedToUtc() throws Exception {
        assertEquals(LocalDateTime.of(2026, 9, 29, 1, 0),
                mapper().readValue("\"2026-09-29T09:00:00+08:00\"", LocalDateTime.class));
    }

    @Test
    void legacyLocalInputUsesDeclaredServiceTimezone() throws Exception {
        assertEquals(LocalDateTime.of(2026, 9, 29, 1, 0),
                mapper().readValue("\"2026-09-29 09:00:00\"", LocalDateTime.class));
    }
}
