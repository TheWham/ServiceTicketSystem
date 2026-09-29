package com.itticket.rag.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

/**
 * ============================================================================
 * 知识正文 JSON 读写工具 (KnowledgeContent)
 * ============================================================================
 *
 * <p>权威模型把知识正文存于 {@code knowledge_version.content_json}，键为
 * {@code title / summary / keywords / body}（见 db/init/00-schema.sql 的 search_text 生成列）。
 * 本工具统一读写这四个键，避免各处手拼 JSON 造成键名漂移。</p>
 *
 * <p>读取侧对脏数据容错：非 JSON、缺键、空值都退化为可用的兜底值，
 * 不因单条历史数据异常而中断检索或索引重建。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
public final class KnowledgeContent {

    /** 标题缺失时的占位（契约要求 title 非空） */
    public static final String TITLE_PLACEHOLDER = "（未命名知识）";

    /** 权威模型的四个键 */
    public static final String KEY_TITLE = "title";
    public static final String KEY_SUMMARY = "summary";
    public static final String KEY_KEYWORDS = "keywords";
    public static final String KEY_BODY = "body";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private KnowledgeContent() {
    }

    /** 组装 content_json；缺失的键写入空串，保证四个键始终存在 */
    public static String build(String title, String summary, String keywords, String body) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put(KEY_TITLE, blankToEmpty(title));
        node.put(KEY_SUMMARY, blankToEmpty(summary));
        node.put(KEY_KEYWORDS, blankToEmpty(keywords));
        node.put(KEY_BODY, blankToEmpty(body));
        try {
            return MAPPER.writeValueAsString(node);
        } catch (Exception e) {
            throw new IllegalStateException("知识正文 content_json 序列化失败: " + e.getMessage(), e);
        }
    }

    /** 提取标题；缺失时依次回退到摘要、正文片段、占位符 */
    public static String titleOf(String contentJson) {
        JsonNode node = parse(contentJson);
        if (node == null) {
            // 非 JSON 内容：直接以原文兜底
            String raw = contentJson == null ? "" : contentJson.trim();
            return raw.isBlank() ? TITLE_PLACEHOLDER : truncate(raw, 60);
        }
        String title = textOf(node, KEY_TITLE);
        if (!title.isBlank()) {
            return title;
        }
        String summary = textOf(node, KEY_SUMMARY);
        if (!summary.isBlank()) {
            return truncate(summary, 60);
        }
        String body = textOf(node, KEY_BODY);
        if (!body.isBlank()) {
            return truncate(body, 60);
        }
        return TITLE_PLACEHOLDER;
    }

    /** 提取正文；无 body 键时回退整段文本 */
    public static String bodyOf(String contentJson) {
        JsonNode node = parse(contentJson);
        if (node == null) {
            return contentJson == null ? "" : contentJson;
        }
        String body = textOf(node, KEY_BODY);
        return body.isBlank() ? node.toString() : body;
    }

    /** 提取摘要 */
    public static String summaryOf(String contentJson) {
        JsonNode node = parse(contentJson);
        return node == null ? "" : textOf(node, KEY_SUMMARY);
    }

    /** 关键词（空格分隔，用于检索辅助与调试） */
    public static String keywordsOf(String contentJson) {
        JsonNode node = parse(contentJson);
        return node == null ? "" : textOf(node, KEY_KEYWORDS);
    }

    private static JsonNode parse(String contentJson) {
        if (contentJson == null || contentJson.isBlank()) {
            return null;
        }
        try {
            JsonNode node = MAPPER.readTree(contentJson);
            return node != null && node.isObject() ? node : null;
        } catch (Exception e) {
            return null;
        }
    }

    private static String textOf(JsonNode node, String key) {
        JsonNode value = node.path(key);
        return value.isMissingNode() || value.isNull() ? "" : value.asText("").trim();
    }

    private static String blankToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private static String truncate(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }
}
