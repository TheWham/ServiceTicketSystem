package com.itticket.common.web;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.datatype.jsr310.deser.LocalDateTimeDeserializer;
import com.fasterxml.jackson.datatype.jsr310.ser.LocalDateTimeSerializer;
import org.springframework.boot.autoconfigure.jackson.Jackson2ObjectMapperBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;

/**
 * Jackson 时间格式统一为 "yyyy-MM-dd HH:mm:ss"(与旧版 SQLite/MySQL 存储展示格式一致)。
 * 反序列化兼容:ISO(yyyy-MM-dd'T'HH:mm:ss)、前端 datetime-local(yyyy-MM-dd'T'HH:mm)、
 * 标准格式(yyyy-MM-dd HH:mm:ss)。
 */
@Configuration
public class JacksonTimeConfig {

    public static final DateTimeFormatter DISPLAY = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Bean
    public Jackson2ObjectMapperBuilderCustomizer localDateTimeCustomizer() {
        return builder -> builder
                .serializers(new LocalDateTimeSerializer(DISPLAY))
                .deserializers(new LocalDateTimeDeserializer(DISPLAY) {
                    @Override
                    public LocalDateTime deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
                        String text = p.getValueAsString();
                        if (text == null || text.isBlank()) {
                            return null;
                        }
                        List<DateTimeFormatter> formats = List.of(
                                DISPLAY,
                                DateTimeFormatter.ISO_LOCAL_DATE_TIME,
                                DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm"));
                        for (DateTimeFormatter fmt : formats) {
                            try {
                                return LocalDateTime.parse(text, fmt);
                            } catch (DateTimeParseException ignored) {
                                // 尝试下一种格式
                            }
                        }
                        throw new DateTimeParseException("无法解析时间: " + text, text, 0);
                    }
                });
    }
}
