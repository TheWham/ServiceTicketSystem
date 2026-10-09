package com.itticket.rag.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.config.DifyProperties;
import lombok.Builder;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * ============================================================================
 * Dify 知识库 API 客户端 (DifyDatasetClient)
 * ============================================================================
 *
 * 【业务背景与职责】：
 * 对接 Dify Dataset API（知识库服务 API），把文档上传、混合索引（向量+全文）、
 * 向量化处理与召回检索委托给 Dify 平台完成：
 * 1. 知识库管理：创建空知识库（POST /datasets）、列表查询（GET /datasets）；
 * 2. 文档摄入：按文件上传（POST /datasets/{id}/document/create-by-file，multipart）
 *    或按文本创建（POST /datasets/{id}/document/create-by-text）——Dify 侧负责
 *    解析、清洗、分块与向量化，异步返回 batch；
 * 3. 索引状态轮询：GET /datasets/{id}/documents/{batch}/indexing-status；
 * 4. 混合召回：POST /datasets/{id}/retrieve（hybrid_search / semantic_search / full_text_search）。
 *
 * 【降级语义】：凭据缺失或调用失败一律抛 BizException，不静默返回空结果，
 * 由上层（DifyKnowledgeService）决定降级或提示。密钥仅经环境变量注入，禁止入日志。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DifyDatasetClient {

    private final DifyProperties properties;
    private final ObjectMapper objectMapper;

    private static final HttpClient HTTP_CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    /** 知识库（dataset）基本信息 */
    @Data
    @Builder
    public static class Dataset {
        private String id;
        private String name;
        private String indexingTechnique;
        private Integer documentCount;
    }

    /** 文档创建结果：Dify 异步摄入，返回 batch 与文档记录 */
    @Data
    @Builder
    public static class DocumentCreateResult {
        /** 批次 ID，用于轮询索引状态 */
        private String batch;
        /** 文档 ID */
        private String documentId;
        /** 文档名称 */
        private String documentName;
        /** 创建时的索引状态（通常为 waiting / parsing） */
        private String indexingStatus;
    }

    /** 单个文档的索引进度 */
    @Data
    @Builder
    public static class IndexingStatus {
        private String documentId;
        /** waiting / parsing / cleaning / splitting / indexing / completed / error */
        private String indexingStatus;
        private Integer wordCount;
        private String error;
        private Long completedAt;
    }

    /** 召回结果中的单个分段 */
    @Data
    @Builder
    public static class RetrievedRecord {
        private String segmentId;
        private Integer position;
        private String documentId;
        private String documentName;
        private String content;
        private List<String> keywords;
        private Double score;
        private String hitCountingMethod;
    }

    /** 召回（retrieve）完整响应 */
    @Data
    @Builder
    public static class RetrieveResult {
        private String query;
        private List<RetrievedRecord> records;
    }

    /**
     * 确保目标知识库存在：配置了 dataset-id 直接返回；否则按名称查找，找不到则创建空知识库。
     */
    public Dataset ensureDataset() {
        if (isBlank(properties.getDatasetId())) {
            Dataset found = findDatasetByName(properties.getDatasetName());
            if (found != null) {
                properties.setDatasetId(found.getId());
                log.info("复用已存在的 Dify 知识库: id={}, name={}", found.getId(), found.getName());
                return found;
            }
            return createDataset(properties.getDatasetName(), properties.getIndexingTechnique());
        }
        return Dataset.builder().id(properties.getDatasetId()).build();
    }

    /** 创建空知识库（POST /datasets） */
    public Dataset createDataset(String name, String indexingTechnique) {
        ObjectNode body = objectMapper.createObjectNode();
        body.put("name", name);
        body.put("indexing_technique", indexingTechnique);
        body.put("description", "IT 服务工单系统 rag-service 知识库（Dify 通道）");
        JsonNode resp = exchange("POST", "/datasets", body, "创建 Dify 知识库失败");
        Dataset dataset = Dataset.builder()
                .id(text(resp, "id"))
                .name(text(resp, "name"))
                .indexingTechnique(text(resp, "indexing_technique"))
                .documentCount(intOrNull(resp, "document_count"))
                .build();
        properties.setDatasetId(dataset.getId());
        log.info("已创建 Dify 知识库: id={}, name={}", dataset.getId(), dataset.getName());
        return dataset;
    }

    /** 按名称在知识库列表中查找（GET /datasets） */
    public Dataset findDatasetByName(String name) {
        JsonNode resp = exchange("GET", "/datasets?page=1&limit=100", null, "查询 Dify 知识库列表失败");
        JsonNode data = resp.get("data");
        if (data == null || !data.isArray()) {
            return null;
        }
        for (JsonNode item : data) {
            if (name != null && name.equals(text(item, "name"))) {
                return Dataset.builder()
                        .id(text(item, "id"))
                        .name(text(item, "name"))
                        .indexingTechnique(text(item, "indexing_technique"))
                        .documentCount(intOrNull(item, "document_count"))
                        .build();
            }
        }
        return null;
    }

    /**
     * 按文件上传文档（POST /datasets/{id}/document/create-by-file）。
     * Dify 侧完成解析、分块与向量化；返回 batch 用于状态轮询。
     *
     * @param fileName     文件名（含扩展名，Dify 据此判定解析器）
     * @param fileBytes    文件内容
     * @param chunkSize    自定义切片长度；&lt;=0 时使用 Dify 自动分段
     * @param chunkOverlap 自定义切片重叠长度
     */
    public DocumentCreateResult createDocumentByFile(String fileName, byte[] fileBytes,
                                                     int chunkSize, int chunkOverlap) {
        String datasetId = requireDatasetId();
        String path = "/datasets/" + datasetId + "/document/create-by-file";

        String dataJson = buildProcessRuleJson(chunkSize, chunkOverlap);
        byte[] body = buildMultipart(fileBytes, fileName, dataJson);

        JsonNode resp = send(buildRequest("POST", path)
                .header("Content-Type", "multipart/form-data; boundary=" + MULTIPART_BOUNDARY)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body)), "上传文档到 Dify 失败");

        return parseDocumentCreateResult(resp, fileName);
    }

    /**
     * 按文本创建文档（POST /datasets/{id}/document/create-by-text）。
     *
     * @param name         文档名称
     * @param text         文档正文
     * @param chunkSize    自定义切片长度；&lt;=0 时使用 Dify 自动分段
     * @param chunkOverlap 自定义切片重叠长度
     */
    public DocumentCreateResult createDocumentByText(String name, String text,
                                                     int chunkSize, int chunkOverlap) {
        String datasetId = requireDatasetId();
        String path = "/datasets/" + datasetId + "/document/create-by-text";

        ObjectNode body = objectMapper.createObjectNode();
        body.put("name", name);
        body.put("text", text);
        body.put("indexing_technique", properties.getIndexingTechnique());
        body.put("doc_form", "text_model");
        body.set("process_rule", buildProcessRule(chunkSize, chunkOverlap));

        JsonNode resp = exchange("POST", path, body, "按文本创建 Dify 文档失败");
        return parseDocumentCreateResult(resp, name);
    }

    /** 查询批次索引状态（GET /datasets/{id}/documents/{batch}/indexing-status） */
    public List<IndexingStatus> getIndexingStatus(String batch) {
        String datasetId = requireDatasetId();
        String path = "/datasets/" + datasetId + "/documents/" + batch + "/indexing-status";
        JsonNode resp = exchange("GET", path, null, "查询 Dify 索引状态失败");
        List<IndexingStatus> statuses = new ArrayList<>();
        JsonNode data = resp.get("data");
        if (data != null && data.isArray()) {
            for (JsonNode item : data) {
                statuses.add(IndexingStatus.builder()
                        .documentId(text(item, "id"))
                        .indexingStatus(text(item, "indexing_status"))
                        .wordCount(intOrNull(item, "word_count"))
                        .error(text(item, "error"))
                        .completedAt(longOrNull(item, "completed_at"))
                        .build());
            }
        }
        return statuses;
    }

    /**
     * 混合召回（POST /datasets/{id}/retrieve）。
     *
     * @param query          检索问题
     * @param searchMethod   hybrid_search / semantic_search / full_text_search；空则取配置默认
     * @param topK           召回条数；&lt;=0 取配置默认
     * @param scoreThreshold 分数阈值；null 取配置默认
     */
    public RetrieveResult retrieve(String query, String searchMethod, Integer topK, Double scoreThreshold) {
        String datasetId = requireDatasetId();
        String path = "/datasets/" + datasetId + "/retrieve";

        String method = isBlank(searchMethod) ? properties.getSearchMethod() : searchMethod;
        int k = topK == null || topK <= 0
                ? (properties.getTopK() == null ? 5 : properties.getTopK())
                : topK;
        double threshold = scoreThreshold == null
                ? (properties.getScoreThreshold() == null ? 0.3 : properties.getScoreThreshold())
                : scoreThreshold;

        ObjectNode body = objectMapper.createObjectNode();
        body.put("query", query);
        ObjectNode retrievalModel = body.putObject("retrieval_model");
        retrievalModel.put("search_method", method);
        retrievalModel.put("reranking_enable", false);
        retrievalModel.put("top_k", k);
        retrievalModel.put("score_threshold_enabled", threshold > 0);
        if (threshold > 0) {
            retrievalModel.put("score_threshold", threshold);
        }

        JsonNode resp = exchange("POST", path, body, "Dify 召回失败");
        List<RetrievedRecord> records = new ArrayList<>();
        JsonNode data = resp.get("records");
        if (data != null && data.isArray()) {
            for (JsonNode item : data) {
                JsonNode segment = item.get("segment");
                RetrievedRecord.RetrievedRecordBuilder builder = RetrievedRecord.builder()
                        .content(text(item, "content"))
                        .score(doubleOrNull(item, "score"))
                        .hitCountingMethod(text(item, "hit_counting_method"));
                if (segment != null && !segment.isNull()) {
                    builder.segmentId(text(segment, "id"))
                            .position(intOrNull(segment, "position"))
                            .keywords(textArray(segment, "keywords"));
                    JsonNode document = segment.get("document");
                    if (document != null && !document.isNull()) {
                        builder.documentId(text(document, "id"))
                                .documentName(text(document, "name"));
                    }
                }
                records.add(builder.build());
            }
        }
        String echoedQuery = resp.has("query") && resp.get("query").isObject()
                ? text(resp.get("query"), "content") : query;
        return RetrieveResult.builder().query(echoedQuery).records(records).build();
    }

    // ==================== 内部工具 ====================

    private DocumentCreateResult parseDocumentCreateResult(JsonNode resp, String fallbackName) {
        JsonNode doc = resp.get("document");
        if (doc == null || doc.isNull()) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "Dify 文档创建响应缺少 document 节点");
        }
        return DocumentCreateResult.builder()
                .batch(text(resp, "batch"))
                .documentId(text(doc, "id"))
                .documentName(isBlank(text(doc, "name")) ? fallbackName : text(doc, "name"))
                .indexingStatus(text(doc, "indexing_status"))
                .build();
    }

    private String buildProcessRuleJson(int chunkSize, int chunkOverlap) {
        ObjectNode root = objectMapper.createObjectNode();
        root.put("indexing_technique", properties.getIndexingTechnique());
        root.put("doc_form", "text_model");
        root.set("process_rule", buildProcessRule(chunkSize, chunkOverlap));
        try {
            return objectMapper.writeValueAsString(root);
        } catch (Exception e) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "构造 Dify 上传参数失败: " + e.getMessage());
        }
    }

    /** 分段规则：chunkSize<=0 走 automatic，否则走 custom rules */
    private ObjectNode buildProcessRule(int chunkSize, int chunkOverlap) {
        ObjectNode rule = objectMapper.createObjectNode();
        if (chunkSize <= 0) {
            rule.put("mode", "automatic");
            return rule;
        }
        rule.put("mode", "custom");
        ObjectNode rules = rule.putObject("rules");
        rules.put("pre_processing_rules", objectMapper.createArrayNode()
                .add(objectMapper.createObjectNode().put("id", "remove_extra_spaces").put("enabled", true))
                .add(objectMapper.createObjectNode().put("id", "remove_urls_emails").put("enabled", false)));
        rules.put("segmentation", objectMapper.createObjectNode()
                .put("separator", "\n\n")
                .put("max_tokens", chunkSize)
                .put("chunk_overlap", Math.max(chunkOverlap, 0)));
        return rule;
    }

    private String requireDatasetId() {
        String datasetId = properties.getDatasetId();
        if (isBlank(datasetId)) {
            throw new BizException(ErrorCode.PARAM_INVALID,
                    "Dify 知识库未初始化：请先配置 rag.dify.dataset-id 或调用 POST /api/v1/rag/dify/datasets");
        }
        return datasetId;
    }

    private JsonNode exchange(String method, String path, JsonNode body, String errorPrefix) {
        try {
            HttpRequest.Builder builder = buildRequest(method, path);
            if (body == null) {
                builder = builder.method(method, HttpRequest.BodyPublishers.noBody());
            } else {
                builder = builder.header("Content-Type", "application/json")
                        .method(method, HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(body)));
            }
            return send(builder, errorPrefix);
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("Dify API 调用异常: {}", e.getMessage(), e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, errorPrefix + ": " + e.getMessage());
        }
    }

    private HttpRequest.Builder buildRequest(String method, String path) {
        if (isBlank(properties.getApiKey())) {
            // 凭据缺失按依赖不可用处理（对齐 MR-002 密钥治理：不内置明文默认值）
            throw new BizException(ErrorCode.SYSTEM_ERROR,
                    "Dify 凭据未配置：请通过环境变量 DIFY_API_KEY 注入");
        }
        return HttpRequest.newBuilder()
                .uri(URI.create(baseUrl() + path))
                .header("Authorization", "Bearer " + properties.getApiKey())
                .timeout(Duration.ofSeconds(properties.getTimeoutSeconds() == null ? 30 : properties.getTimeoutSeconds()));
    }

    private JsonNode send(HttpRequest.Builder builder, String errorPrefix) {
        try {
            HttpResponse<String> response = HTTP_CLIENT.send(builder.build(), HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                log.error("Dify API HTTP Error [{}]: {}", response.statusCode(), response.body());
                throw new BizException(ErrorCode.SYSTEM_ERROR,
                        errorPrefix + " [" + response.statusCode() + "]: " + extractErrorMessage(response.body()));
            }
            if (isBlank(response.body())) {
                return objectMapper.createObjectNode();
            }
            return objectMapper.readTree(response.body());
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("Dify API 调用异常: {}", e.getMessage(), e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, errorPrefix + ": " + e.getMessage());
        }
    }

    private String baseUrl() {
        String url = properties.getBaseUrl() == null ? "" : properties.getBaseUrl().trim();
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        return url;
    }

    private String extractErrorMessage(String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            if (root.has("message")) {
                return root.get("message").asText();
            }
            if (root.has("code")) {
                return text(root, "code");
            }
        } catch (Exception ignored) {
        }
        return responseBody;
    }

    /** multipart 分隔符：body 与 Content-Type 头必须使用同一值 */
    static final String MULTIPART_BOUNDARY = "----itTicketRagDifyBoundary";

    /** 手工构造 multipart/form-data（file + data 两个 part） */
    private byte[] buildMultipart(byte[] fileBytes, String fileName, String dataJson) {
        try {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            String boundary = MULTIPART_BOUNDARY;
            // part 1: file
            out.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
            out.write(("Content-Disposition: form-data; name=\"file\"; filename=\""
                    + sanitizeFileName(fileName) + "\"\r\n").getBytes(StandardCharsets.UTF_8));
            out.write("Content-Type: application/octet-stream\r\n\r\n".getBytes(StandardCharsets.UTF_8));
            out.write(fileBytes);
            out.write("\r\n".getBytes(StandardCharsets.UTF_8));
            // part 2: data (JSON 字符串)
            out.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
            out.write("Content-Disposition: form-data; name=\"data\"\r\n".getBytes(StandardCharsets.UTF_8));
            out.write("Content-Type: application/json\r\n\r\n".getBytes(StandardCharsets.UTF_8));
            out.write(dataJson.getBytes(StandardCharsets.UTF_8));
            out.write("\r\n".getBytes(StandardCharsets.UTF_8));
            out.write(("--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
            return out.toByteArray();
        } catch (Exception e) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "构造 multipart 请求体失败: " + e.getMessage());
        }
    }

    private String sanitizeFileName(String fileName) {
        if (fileName == null || fileName.isBlank()) {
            return "document.md";
        }
        return fileName.replaceAll("[\"\\r\\n]", "_");
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }

    private static String text(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? null : v.asText();
    }

    private static Integer intOrNull(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? null : v.asInt();
    }

    private static Long longOrNull(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? null : v.asLong();
    }

    private static Double doubleOrNull(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return v == null || v.isNull() ? null : v.asDouble();
    }

    private static List<String> textArray(JsonNode node, String field) {
        JsonNode v = node.get(field);
        if (v == null || !v.isArray()) {
            return List.of();
        }
        List<String> list = new ArrayList<>();
        for (JsonNode item : v) {
            list.add(item.asText());
        }
        return list;
    }
}
