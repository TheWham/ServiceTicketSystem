package com.itticket.consultation.support;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.util.List;
import java.util.Map;

/**
 * 持久化 JSON 列与事件 payload 的序列化。
 *
 * <p>独立于 Web 层 ObjectMapper:common-web 为兼容旧接口改写了全局时间格式,
 * 而 JSON 列与事件 envelope 必须稳定、可重放,不能跟随展示层配置变化(EV-007)。
 * 属性按字典序输出,保证 requestHash 对同一请求体稳定(RD-002)。
 */
public final class Json {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private Json() {
    }

    public static String write(Object value) {
        if (value == null) {
            return null;
        }
        try {
            return MAPPER.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("JSON 序列化失败: " + value.getClass().getName(), e);
        }
    }

    public static <T> T read(String json, Class<T> type) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return MAPPER.readValue(json, type);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("JSON 反序列化失败: " + type.getName(), e);
        }
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> readMap(String json) {
        return read(json, Map.class);
    }

    @SuppressWarnings("unchecked")
    public static List<Map<String, Object>> readList(String json) {
        return read(json, List.class);
    }
}
