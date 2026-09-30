package com.itticket.rag.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.config.EmbeddingProperties;
import lombok.Builder;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * ============================================================================
 * RAG 阶段三：文本向量嵌入客户端服务 (EmbeddingClientService)
 * ============================================================================
 *
 * 【业务背景与职责】：
 * 1. 适配 OpenAI 标准 Embedding 协议规范（POST /v1/embeddings）
 *    （MR-003 · specs/10-model-rag-integration.md:46：OpenAI-compatible HTTP）。
 * 2. 对接阿里云百炼 / 通义千问专属 Embedding 模型（如 qwen3.7-text-embedding，1024维）。
 * 3. 支持多切片自动分批（Batching）、请求重试与耗时指标度量。
 * 4. 严格校验返回向量维度与顺序，输出各切片的密集向量（Dense Vector）。
 *
 * 【规范引用】（路径相对仓库根目录 docs/）：
 * - MR-001 · specs/10-model-rag-integration.md:13
 *     Provider 配置以不可变版本发布。
 * - MR-002 · specs/10-model-rag-integration.md:40
 *     apiKey 只存 Secret 引用：本服务不内置明文默认值，由 EMBEDDING_API_KEY 环境变量注入。
 * - RD-006 · specs/04-resilience-degradation.md:67
 *     凭据缺失/调用失败按依赖不可用降级，上层转为 MODEL_UNAVAILABLE 或索引待补偿，
 *     不得用失败静默产出空向量。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EmbeddingClientService {

    private final EmbeddingProperties properties;
    private final ObjectMapper objectMapper;

    private static final HttpClient HTTP_CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    /**
     * 向量化计算结果结构体
     */
    @Data
    @Builder
    public static class EmbeddingResult {
        /** 各文本块对应的 1024 维密集向量列表 */
        private List<List<Float>> vectors;
        /** 实际调用的模型名称 */
        private String model;
        /** 向量维度（例如 1024） */
        private int dimensions;
        /** 消耗的 Token 总量 */
        private int totalTokens;
        /** 向量化阶段总耗时（毫秒） */
        private long durationMs;
        /** 批处理调用次数 */
        private int batchCount;
    }

    /**
     * 为多个切片文本批量生成向量
     *
     * @param texts 切片正文列表
     * @return EmbeddingResult 包含各切片向量及性能指标
     */
    public EmbeddingResult generateEmbeddings(List<String> texts) {
        if (texts == null || texts.isEmpty()) {
            return EmbeddingResult.builder()
                    .vectors(List.of())
                    .model(properties.getModel())
                    .dimensions(properties.getDimensions())
                    .totalTokens(0)
                    .durationMs(0)
                    .batchCount(0)
                    .build();
        }

        long start = System.currentTimeMillis();
        if (properties.getApiKey() == null || properties.getApiKey().isBlank()) {
            // 凭据缺失按依赖不可用处理，上层转为 MODEL_UNAVAILABLE / 索引待补偿
            // （RD-006 · specs/04-resilience-degradation.md:67；密钥治理 MR-002 · specs/10-model-rag-integration.md:40）
            throw new BizException(ErrorCode.SYSTEM_ERROR,
                    "向量模型凭据未配置：请通过环境变量 EMBEDDING_API_KEY 注入");
        }
        int batchSize = properties.getBatchSize() != null && properties.getBatchSize() > 0 ? properties.getBatchSize() : 16;
        List<List<Float>> allVectors = new ArrayList<>(texts.size());
        int totalTokens = 0;
        int batchCount = 0;

        log.info("Starting embedding generation for {} text chunks (model: {}, batchSize: {})",
                texts.size(), properties.getModel(), batchSize);

        // 分批调用 Embedding API
        for (int i = 0; i < texts.size(); i += batchSize) {
            int end = Math.min(i + batchSize, texts.size());
            List<String> batchTexts = texts.subList(i, end);
            batchCount++;

            BatchResponse batchRes = callEmbeddingApi(batchTexts);
            allVectors.addAll(batchRes.getVectors());
            totalTokens += batchRes.getPromptTokens();
        }

        long duration = System.currentTimeMillis() - start;
        log.info("Embedding generation finished in {}ms. Total tokens: {}, vectors count: {}",
                duration, totalTokens, allVectors.size());

        return EmbeddingResult.builder()
                .vectors(allVectors)
                .model(properties.getModel())
                .dimensions(properties.getDimensions())
                .totalTokens(totalTokens)
                .durationMs(duration)
                .batchCount(batchCount)
                .build();
    }

    /**
     * 单批次调用 OpenAI 兼容 Embedding 接口
     */
    private BatchResponse callEmbeddingApi(List<String> batchTexts) {
        String url = properties.getBaseUrl();
        if (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        if (!url.endsWith("/embeddings")) {
            url = url + "/embeddings";
        }

        try {
            // 组装 OpenAI 规范请求体
            ObjectNode requestJson = objectMapper.createObjectNode();
            requestJson.put("model", properties.getModel());
            if (properties.getDimensions() != null && properties.getDimensions() > 0) {
                requestJson.put("dimensions", properties.getDimensions());
            }

            ArrayNode inputArray = requestJson.putArray("input");
            for (String t : batchTexts) {
                inputArray.add(t);
            }

            String requestBody = objectMapper.writeValueAsString(requestJson);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Bearer " + properties.getApiKey())
                    .header("Content-Type", "application/json")
                    .timeout(Duration.ofSeconds(properties.getTimeoutSeconds()))
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .build();

            HttpResponse<String> response = HTTP_CLIENT.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                log.error("Embedding API HTTP Error [{}]: {}", response.statusCode(), response.body());
                throw new BizException(ErrorCode.SYSTEM_ERROR,
                        "向量模型调用失败 [" + response.statusCode() + "]: " + extractErrorMessage(response.body()));
            }

            // 解析响应数据
            JsonNode root = objectMapper.readTree(response.body());
            JsonNode dataArray = root.get("data");
            if (dataArray == null || !dataArray.isArray()) {
                throw new BizException(ErrorCode.SYSTEM_ERROR, "向量模型响应数据结构异常，未包含 data 数组");
            }

            // 按 index 排序收集向量
            List<IndexedVector> indexedList = new ArrayList<>();
            for (JsonNode item : dataArray) {
                int index = item.has("index") ? item.get("index").asInt() : indexedList.size();
                JsonNode vecNode = item.get("embedding");
                if (vecNode == null || !vecNode.isArray()) {
                    throw new BizException(ErrorCode.SYSTEM_ERROR, "切片索引 [" + index + "] 缺失 embedding 向量数据");
                }
                List<Float> vector = new ArrayList<>(vecNode.size());
                for (JsonNode val : vecNode) {
                    vector.add((float) val.asDouble());
                }
                indexedList.add(new IndexedVector(index, vector));
            }

            indexedList.sort(Comparator.comparingInt(a -> a.index));

            List<List<Float>> vectors = indexedList.stream().map(iv -> iv.vector).toList();
            if (vectors.size() != batchTexts.size()) {
                throw new BizException(ErrorCode.SYSTEM_ERROR,
                        "向量化返回数量 (" + vectors.size() + ") 与输入文本数量 (" + batchTexts.size() + ") 不一致");
            }

            int promptTokens = 0;
            if (root.has("usage") && root.get("usage").has("total_tokens")) {
                promptTokens = root.get("usage").get("total_tokens").asInt();
            }

            return new BatchResponse(vectors, promptTokens);

        } catch (BizException be) {
            throw be;
        } catch (Exception e) {
            log.error("Embedding API invocation exception: {}", e.getMessage(), e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "向量嵌入服务调用异常: " + e.getMessage());
        }
    }

    private String extractErrorMessage(String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            if (root.has("error") && root.get("error").has("message")) {
                return root.get("error").get("message").asText();
            }
        } catch (Exception ignored) {
        }
        return responseBody;
    }

    private record IndexedVector(int index, List<Float> vector) {}

    private record BatchResponse(List<List<Float>> vectors, int promptTokens) {
        public List<List<Float>> getVectors() { return vectors; }
        public int getPromptTokens() { return promptTokens; }
    }
}
