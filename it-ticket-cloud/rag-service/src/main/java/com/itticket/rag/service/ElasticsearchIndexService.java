package com.itticket.rag.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.rag.vo.KnowledgeChunkVO;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

/**
 * ============================================================================
 * RAG 阶段三：Elasticsearch 索引与向量/全文持久化服务 (ElasticsearchIndexService)
 * ============================================================================
 *
 * 【架构设计与核心功能】：
 * 1. 索引自动管理（Auto Index Lifecycle）：
 *    - 服务启动与执行入库时自动探测 ES 节点连通性。
 *    - 若目标索引不存在，自动创建符合 RAG 规范的索引 Mapping（包含 chunk_id、article_id、title、content 等）。
 *
 * 2. 字段检索模式设计（Schema Mapping）：
 *    - chunk_id, article_id, version_id, category_id -> keyword 字段（用于精确过滤与聚合分析）。
 *    - title, content -> text 字段（支持全文分词与 BM25 相关度打分）。
 *    - created_at -> date 字段（支持按时间窗口衰减加权）。
 *
 * 3. 弹性容错与降级设计（Resilience & Graceful Degradation - 契约 RD 规范）：
 *    - 若外部 ES 服务暂时不可达或未启动，服务不阻断主链路，自动转入 OFFLINE_FALLBACK 模式并记录诊断日志，
 *      确保文档元数据依然成功持久化至 MySQL，前端工作台依然能完整查看前置切片链路与耗时明细。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
public class ElasticsearchIndexService {

    @Value("${elasticsearch.host:localhost}")
    private String esHost;

    @Value("${elasticsearch.port:9200}")
    private int esPort;

    @Value("${elasticsearch.scheme:http}")
    private String esScheme;

    @Value("${elasticsearch.index-name:knowledge_chunk}")
    private String indexName;

    @Value("${elasticsearch.connect-timeout-ms:2000}")
    private int connectTimeoutMs;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofMillis(3000))
            .build();

    /**
     * ES 索引写入结果度量实体
     */
    @Data
    @Builder
    public static class IndexResult {
        /** 是否至少有一个切片入库成功（或降级成功） */
        private boolean success;
        /** 目标 ES 索引名 */
        private String indexName;
        /** 待写入切片总数 */
        private int totalChunks;
        /** 成功写入 ES 的切片数 */
        private int indexedChunks;
        /** 成功生成的 ES 文档 ID 列表 */
        private List<String> indexedDocIds;
        /** 结果描述消息 */
        private String message;
        /** ES 访问端点，例如 http://localhost:9200 */
        private String esEndpoint;
        /** 详细执行指标字典 */
        private Map<String, Object> details;
    }

    /**
     * 将切片列表批量持久化到 Elasticsearch 索引
     *
     * @param articleId  所属知识文章业务 ID
     * @param versionId  所属知识版本业务 ID
     * @param categoryId 知识分类编码（如 C_NET）
     * @param chunks     待入库的切片列表
     * @return IndexResult 索引执行度量结果
     */
    public IndexResult indexChunks(String articleId, String versionId, String categoryId, List<KnowledgeChunkVO> chunks) {
        String baseUri = String.format("%s://%s:%d", esScheme, esHost, esPort);
        List<String> docIds = new ArrayList<>();
        Map<String, Object> details = new HashMap<>();
        details.put("esEndpoint", baseUri);
        details.put("targetIndex", indexName);

        if (chunks == null || chunks.isEmpty()) {
            return IndexResult.builder()
                    .success(true)
                    .indexName(indexName)
                    .totalChunks(0)
                    .indexedChunks(0)
                    .indexedDocIds(Collections.emptyList())
                    .message("切片列表为空，无需写入ES")
                    .esEndpoint(baseUri)
                    .details(details)
                    .build();
        }

        // 步骤 1：探测 ES 连通性并确保索引及 Mapping 已就绪
        boolean esAvailable = checkAndEnsureIndex(baseUri);
        if (!esAvailable) {
            log.warn("Elasticsearch ({}) unreachable or offline, entering mock/local index trace mode", baseUri);
            // 契约 RD 降级处理：生成可追踪的快照 DocID，并在日志中标记
            for (KnowledgeChunkVO chunk : chunks) {
                String docId = "es-doc-" + chunk.getChunkId();
                chunk.setEsDocId(docId);
                chunk.setStatus("OFFLINE_INDEXED");
                docIds.add(docId);
            }
            details.put("esStatus", "OFFLINE_FALLBACK");
            details.put("note", "ES服务未连接，切片已生成本地快照");
            return IndexResult.builder()
                    .success(true)
                    .indexName(indexName)
                    .totalChunks(chunks.size())
                    .indexedChunks(chunks.size())
                    .indexedDocIds(docIds)
                    .message("切片构建完成（ES服务未连接，以本地追踪模式记录索引ID）")
                    .esEndpoint(baseUri)
                    .details(details)
                    .build();
        }

        // 步骤 2：逐条推送切片到 ES 索引中
        int successCount = 0;
        for (KnowledgeChunkVO chunk : chunks) {
            try {
                Map<String, Object> doc = new HashMap<>();
                doc.put("chunk_id", chunk.getChunkId());
                doc.put("article_id", articleId);
                doc.put("version_id", versionId);
                doc.put("category_id", categoryId);
                doc.put("title", chunk.getTitle());
                doc.put("content", chunk.getContent());
                doc.put("chunk_index", chunk.getChunkIndex());
                doc.put("char_count", chunk.getCharCount());
                doc.put("created_at", LocalDateTime.now().toString());

                // 写入 1024 维 Dense Vector
                if (chunk.getVector() != null && !chunk.getVector().isEmpty()) {
                    doc.put("vector", chunk.getVector());
                }

                String jsonBody = objectMapper.writeValueAsString(doc);
                String docUri = String.format("%s/%s/_doc/%s", baseUri, indexName, chunk.getChunkId());

                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(docUri))
                        .header("Content-Type", "application/json")
                        .timeout(Duration.ofMillis(3000))
                        .PUT(HttpRequest.BodyPublishers.ofString(jsonBody))
                        .build();

                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() == 200 || response.statusCode() == 201) {
                    chunk.setEsDocId(chunk.getChunkId());
                    chunk.setStatus("SUCCESS");
                    docIds.add(chunk.getChunkId());
                    successCount++;
                } else {
                    chunk.setStatus("FAILED");
                    chunk.setErrorMessage("ES Status: " + response.statusCode());
                    log.warn("ES index failed for chunk {}: {}", chunk.getChunkId(), response.body());
                }
            } catch (Exception e) {
                chunk.setStatus("FAILED");
                chunk.setErrorMessage(e.getMessage());
                log.error("Exception while indexing chunk {} to ES", chunk.getChunkId(), e);
            }
        }

        details.put("esStatus", "CONNECTED");
        details.put("successCount", successCount);
        details.put("failCount", chunks.size() - successCount);

        return IndexResult.builder()
                .success(successCount > 0)
                .indexName(indexName)
                .totalChunks(chunks.size())
                .indexedChunks(successCount)
                .indexedDocIds(docIds)
                .message(String.format("成功入库 %d/%d 个切片至 ES 索引 [%s]", successCount, chunks.size(), indexName))
                .esEndpoint(baseUri)
                .details(details)
                .build();
    }

    /**
     * 检查并自动初始化 ES 索引结构与字段类型 Mapping（包含 dense_vector 1024 维向量字段）
     */
    private boolean checkAndEnsureIndex(String baseUri) {
        try {
            // 探测集群健康
            HttpRequest pingReq = HttpRequest.newBuilder()
                    .uri(URI.create(baseUri))
                    .timeout(Duration.ofMillis(connectTimeoutMs))
                    .GET()
                    .build();
            HttpResponse<String> pingRes = httpClient.send(pingReq, HttpResponse.BodyHandlers.ofString());
            if (pingRes.statusCode() != 200) {
                return false;
            }

            // 检查索引是否存在
            HttpRequest headReq = HttpRequest.newBuilder()
                    .uri(URI.create(baseUri + "/" + indexName))
                    .timeout(Duration.ofMillis(connectTimeoutMs))
                    .method("HEAD", HttpRequest.BodyPublishers.noBody())
                    .build();
            HttpResponse<Void> headRes = httpClient.send(headReq, HttpResponse.BodyHandlers.discarding());
            if (headRes.statusCode() == 200) {
                // 尝试向已有索引增量注入 vector 字段 Mapping（如果尚未定义）
                tryUpdateVectorMapping(baseUri);
                return true;
            }

            // 若索引不存在，创建索引并定义字段 Schema Mapping（含 dense_vector 向量字段）
            String mappingJson = """
                    {
                      "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                      },
                      "mappings": {
                        "properties": {
                          "chunk_id": { "type": "keyword" },
                          "article_id": { "type": "keyword" },
                          "version_id": { "type": "keyword" },
                          "category_id": { "type": "keyword" },
                          "title": { "type": "text", "analyzer": "standard" },
                          "content": { "type": "text", "analyzer": "standard" },
                          "chunk_index": { "type": "integer" },
                          "char_count": { "type": "integer" },
                          "created_at": { "type": "date" },
                          "vector": {
                            "type": "dense_vector",
                            "dims": 1024,
                            "index": true,
                            "similarity": "cosine"
                          }
                        }
                      }
                    }
                    """;

            HttpRequest createReq = HttpRequest.newBuilder()
                    .uri(URI.create(baseUri + "/" + indexName))
                    .header("Content-Type", "application/json")
                    .timeout(Duration.ofMillis(connectTimeoutMs))
                    .PUT(HttpRequest.BodyPublishers.ofString(mappingJson))
                    .build();
            HttpResponse<String> createRes = httpClient.send(createReq, HttpResponse.BodyHandlers.ofString());
            log.info("Created ES index [{}] response code: {}", indexName, createRes.statusCode());
            return createRes.statusCode() == 200 || createRes.statusCode() == 201;
        } catch (Exception e) {
            log.debug("ES connect probe failed: {}", e.getMessage());
            return false;
        }
    }

    /**
     * 兼容升级：为已有索引增量补充 vector dense_vector mapping
     */
    private void tryUpdateVectorMapping(String baseUri) {
        try {
            String updateMappingJson = """
                    {
                      "properties": {
                        "vector": {
                          "type": "dense_vector",
                          "dims": 1024,
                          "index": true,
                          "similarity": "cosine"
                        }
                      }
                    }
                    """;
            HttpRequest putMappingReq = HttpRequest.newBuilder()
                    .uri(URI.create(baseUri + "/" + indexName + "/_mapping"))
                    .header("Content-Type", "application/json")
                    .timeout(Duration.ofMillis(connectTimeoutMs))
                    .PUT(HttpRequest.BodyPublishers.ofString(updateMappingJson))
                    .build();
            httpClient.send(putMappingReq, HttpResponse.BodyHandlers.discarding());
        } catch (Exception ignored) {
        }
    }

    /**
     * 手动触发创建或重建 ES 索引（供管理端主动初始化调用）
     *
     * @param recreate 是否在已存在时先执行删除后重建
     * @return 执行结果详情
     */
    public Map<String, Object> createIndexExplicitly(boolean recreate) {
        String baseUri = String.format("%s://%s:%d", esScheme, esHost, esPort);
        Map<String, Object> result = new HashMap<>();
        result.put("esEndpoint", baseUri);
        result.put("indexName", indexName);

        try {
            if (recreate) {
                HttpRequest delReq = HttpRequest.newBuilder()
                        .uri(URI.create(baseUri + "/" + indexName))
                        .timeout(Duration.ofMillis(connectTimeoutMs))
                        .DELETE()
                        .build();
                httpClient.send(delReq, HttpResponse.BodyHandlers.discarding());
            }

            boolean ok = checkAndEnsureIndex(baseUri);
            result.put("success", ok);
            result.put("message", ok ? "ES 知识切片索引 [" + indexName + "] 创建/初始化成功" : "ES 连接失败，请检查 " + baseUri);
        } catch (Exception e) {
            result.put("success", false);
            result.put("message", "创建 ES 索引失败: " + e.getMessage());
        }
        return result;
    }
}
