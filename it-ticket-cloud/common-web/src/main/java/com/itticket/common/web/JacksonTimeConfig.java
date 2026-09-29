package com.itticket.common.web;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonGenerator;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.SerializerProvider;
import com.fasterxml.jackson.databind.ser.std.StdSerializer;
import com.fasterxml.jackson.datatype.jsr310.deser.LocalDateTimeDeserializer;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;

/**
 * DM-001/PRD21.1：数据库 LocalDateTime 表示 UTC，HTTP 输出 ISO8601 的 Z 时区。
 * 带时区请求归一 UTC；旧 datetime-local/空格格式按服务时区 Asia/Shanghai 兼容。
 */
@Configuration
public class JacksonTimeConfig {

    public static final DateTimeFormatter DISPLAY = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer localDateTimeCustomizer() {
        return builder -> builder
                .serializers(new StdSerializer<LocalDateTime>(LocalDateTime.class) {
                    @Override
                    public void serialize(LocalDateTime value, JsonGenerator generator,
                                          SerializerProvider provider) throws IOException {
                        generator.writeString(value.atOffset(ZoneOffset.UTC).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
                    }
                })
                .deserializers(new LocalDateTimeDeserializer(DISPLAY) {
                    @Override
                    public LocalDateTime deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
                        String text = p.getValueAsString();
                        if (text == null || text.isBlank()) {
                            return null;
                        }
                        try {
                            return OffsetDateTime.parse(text).withOffsetSameInstant(ZoneOffset.UTC).toLocalDateTime();
                        } catch (DateTimeParseException ignored) {
                            // 兼容旧客户端无时区的本地时间。
                        }
                        List<DateTimeFormatter> formats = List.of(
                                DISPLAY,
                                DateTimeFormatter.ISO_LOCAL_DATE_TIME,
                                DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm"));
                        for (DateTimeFormatter fmt : formats) {
                            try {
                                return LocalDateTime.parse(text, fmt).atZone(ZoneId.of("Asia/Shanghai"))
                                        .withZoneSameInstant(ZoneOffset.UTC).toLocalDateTime();
                            } catch (DateTimeParseException ignored) {
                                // 尝试下一种格式
                            }
                        }
                        throw new DateTimeParseException("无法解析时间: " + text, text, 0);
                    }
                });
    }
}
