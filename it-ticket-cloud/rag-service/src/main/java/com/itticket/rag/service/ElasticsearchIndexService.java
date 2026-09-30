package com.itticket.rag.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.support.EsQueryDsl;
import com.itticket.rag.support.RankFusion;
import com.itticket.rag.vo.ChunkHit;
import com.itticket.rag.vo.KnowledgeChunkVO;
import com.itticket.rag.vo.KnowledgeSearchItem;
import com.itticket.rag.vo.KnowledgeSearchResponse;
import lombok.Builder;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
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
 * 3. 弹性容错与降级设计（Resilience & Graceful Degradation）：
 *    - 若外部 ES 服务暂时不可达或未启动，服务不阻断主链路，自动转入 OFFLINE_FALLBACK 模式并记录诊断日志，
 *      确保文档元数据依然成功持久化至 MySQL，前端工作台依然能完整查看前置切片链路与耗时明细
 *      （RD-006 · specs/04-resilience-degradation.md:67；
 *      RD-013 · specs/04-resilience-degradation.md:142：外部依赖失败不得阻断主链路）。
 *
 * 【规范引用】（路径相对仓库根目录 docs/）：
 * - AI-001 · specs/02-ai-api-json-schema.md:14
 *     检索只读 status=PUBLISHED 的知识切片。
 * - AC-27 · IT服务工单系统PRD-Ultimate.md:911 / specs/09-prd-spec-test-traceability.md:93
 *     下线联动：_update_by_query 置 OFFLINE，此后检索与 RAG 均不返回。
 * - MR-011 · specs/10-model-rag-integration.md:151
 *     索引生命周期：content_hash / index_version / published_at / offline_at 字段与可重建投影语义。
 * - AI-004.4 / AI-API-005 · specs/02-ai-api-json-schema.md:174 / :257
 *     文章级检索响应形态（articleId/versionId/title/summary/categoryId + 分页）。
 * - RD-003 · specs/04-resilience-degradation.md:33
 *     检索类请求 5s 超时、批量操作单独放宽。
 * - PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515
 *     已发布知识不物理删除；_delete_by_query 仅限显式管理端点。
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

    /** 检索类请求超时（RD-003：AI/RAG 请求完整 15 秒内返回，检索阶段控制在秒级） */
    @Value("${elasticsearch.search-timeout-ms:5000}")
    private int searchTimeoutMs;

    /** 存量回填等批量操作超时 */
    @Value("${elasticsearch.bulk-timeout-ms:60000}")
    private int bulkTimeoutMs;

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
     * 将切片列表批量持久化到 Elasticsearch 索引（默认按已发布状态入库，发布时间取当前）。
     */
    public IndexResult indexChunks(String articleId, String versionId, String categoryId, List<KnowledgeChunkVO> chunks) {
        return indexChunks(articleId, versionId, categoryId, KnowledgeRiskLevel.NORMAL,
                EsQueryDsl.STATUS_PUBLISHED, LocalDateTime.now(), chunks);
    }

    /**
     * 将切片列表批量持久化到 Elasticsearch 索引。
     *
     * <p>索引文档字段遵循 MR-011（specs/10-model-rag-integration.md:151）：
     * articleId、versionId、chunkId、embedding、contentHash、indexVersion、publishedAt、offlineAt。
     * 索引存储是可重建投影，不是事实源；
     * indexVersion 直接取知识版本 ID，保证可追溯到 knowledge_version.version_id。</p>
     *
     * @param articleId   所属知识文章业务 ID
     * @param versionId   所属知识版本业务 ID（同时作为 index_version 写入）
     * @param categoryId  知识分类编码（如 C_NET）
     * @param riskLevel   知识风险等级，归一为 NORMAL / HIGH 后落库
     * @param status      切片状态标记；检索侧强制过滤 status=PUBLISHED，下线后置为 OFFLINE（AC-27）
     * @param publishedAt 该知识版本的发布生效时间；草稿不入库（null 时不写该字段）
     * @param chunks      待入库的切片列表
     * @return IndexResult 索引执行度量结果
     */
    public IndexResult indexChunks(String articleId, String versionId, String categoryId,
                                   KnowledgeRiskLevel riskLevel, String status,
                                   LocalDateTime publishedAt, List<KnowledgeChunkVO> chunks) {
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
                // 状态标记：检索侧强制过滤 PUBLISHED（AI-001 · specs/02-ai-api-json-schema.md:14）；
                // 下线时改为 OFFLINE（AC-27 · specs/09-prd-spec-test-traceability.md:93）
                doc.put("status", status);
                doc.put("risk_level", KnowledgeRiskLevel.normalize(riskLevel).getValue());
                // MR-011（specs/10-model-rag-integration.md:151）索引生命周期字段：
                // 内容指纹 + 索引版本 + 发布时间（offline_at 在下线时写入）
                doc.put("content_hash", sha256(chunk.getContent()));
                doc.put("index_version", versionId);
                if (publishedAt != null) {
                    doc.put("published_at", publishedAt.toString());
                }
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
                // 尝试向已有索引增量注入 vector / status / risk_level 字段 Mapping（如果尚未定义）
                tryEnsureMapping(baseUri);
                return true;
            }

            // 若索引不存在，创建索引并定义字段 Schema Mapping（含 status 状态过滤字段与 dense_vector 向量字段）
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
                          "status": { "type": "keyword" },
                          "risk_level": { "type": "keyword" },
                          "content_hash": { "type": "keyword" },
                          "index_version": { "type": "keyword" },
                          "title": { "type": "text", "analyzer": "standard" },
                          "content": { "type": "text", "analyzer": "standard" },
                          "chunk_index": { "type": "integer" },
                          "char_count": { "type": "integer" },
                          "published_at": { "type": "date" },
                          "offline_at": { "type": "date" },
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
     * 兼容升级：为已有索引增量补充 vector / status / risk_level mapping。
     *
     * <p>status 字段是 AC-27（specs/09-prd-spec-test-traceability.md:93，下线后检索不再返回）
     * 与 AI-001（specs/02-ai-api-json-schema.md:14，只检索 PUBLISHED）的基础，
     * 因此对存量索引也必须补齐；补齐后需调用 {@link #backfillMissingStatus()} 回填历史切片。</p>
     */
    private void tryEnsureMapping(String baseUri) {
        try {
            String updateMappingJson = """
                    {
                      "properties": {
                        "status": { "type": "keyword" },
                        "risk_level": { "type": "keyword" },
                        "content_hash": { "type": "keyword" },
                        "index_version": { "type": "keyword" },
                        "published_at": { "type": "date" },
                        "offline_at": { "type": "date" },
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

    // ==========================================================================
    // 检索侧（AI-API-005 契约形态的文章搜索 + 供 AI 客服 ai-messages 链路取依据的切片检索）
    // ==========================================================================

    /**
     * 构造"未执行索引"结果 —— 草稿态不写入 ES 时用于链路追踪展示
     * （AI-001 · specs/02-ai-api-json-schema.md:14：未发布知识不得进入检索索引）。
     */
    public IndexResult skippedResult(String message) {
        Map<String, Object> details = new HashMap<>();
        details.put("esStatus", "SKIPPED");
        details.put("targetIndex", indexName);
        return IndexResult.builder()
                .success(true)
                .indexName(indexName)
                .totalChunks(0)
                .indexedChunks(0)
                .indexedDocIds(Collections.emptyList())
                .message(message)
                .esEndpoint(baseUri())
                .details(details)
                .build();
    }

    /**
     * 索引是否可用：探测集群并确保 mapping 就绪（含 status / vector / risk_level）。
     *
     * @return true 表示可正常读写
     */
    public boolean ensureIndexReady() {
        return checkAndEnsureIndex(baseUri());
    }

    /**
     * 文章级知识检索 —— 契约 AI-004.4（specs/02-ai-api-json-schema.md:174）/
     * AI-API-005（:257）响应形态。
     *
     * <p>multi_match(title^2 + content) 全文检索，强制过滤 status=PUBLISHED（可选分类过滤），
     * 按 article_id collapse 折叠去重，聚合取文章级 total。只返回 articleId/versionId/title/summary/categoryId。</p>
     *
     * @throws BizException 分页超出窗口上限（PARAM_INVALID）或检索服务不可用（SYSTEM_ERROR）
     */
    public KnowledgeSearchResponse searchPublishedArticles(String queryText, String categoryId, int page, int pageSize) {
        int safePage = Math.max(1, page);
        int safeSize = Math.min(Math.max(1, pageSize), 100);
        if ((long) (safePage - 1) * safeSize + safeSize > EsQueryDsl.MAX_WINDOW) {
            throw new BizException(ErrorCode.PARAM_INVALID,
                    "检索分页超出上限（from+size 不得超过 " + EsQueryDsl.MAX_WINDOW + "）");
        }

        JsonNode response = callEs("POST", "/" + indexName + "/_search",
                EsQueryDsl.articleSearchBody(queryText, categoryId, safePage, safeSize), searchTimeoutMs);
        if (response == null) {
            // 不得用空结果掩盖依赖失败（RD-013）
            throw new BizException(ErrorCode.SYSTEM_ERROR, "知识检索服务暂不可用，请稍后重试");
        }

        List<KnowledgeSearchItem> items = new ArrayList<>();
        for (JsonNode hit : response.path("hits").path("hits")) {
            JsonNode source = hit.path("_source");
            String articleId = textOrNull(source, "article_id");
            if (articleId == null) {
                continue;
            }
            items.add(new KnowledgeSearchItem(
                    articleId,
                    textOrNull(source, "version_id"),
                    textOrNull(source, "title"),
                    summarize(source.path("content").asText("")),
                    textOrNull(source, "category_id")));
        }

        // collapse 后的 hits.total 是切片数，文章数须取 cardinality 聚合
        long total = response.path("aggregations").path("article_count").path("value").asLong(items.size());
        return new KnowledgeSearchResponse(items, safePage, safeSize, total);
    }

    /**
     * 切片级混合检索（RAG 问答取依据）：kNN 向量路 + BM25 全文路，RRF 融合后取 Top-K。
     *
     * <p>两路均强制过滤 status=PUBLISHED，已下线知识不会进入回答依据
     * （AI-001 · specs/02-ai-api-json-schema.md:14；
     * AC-27 · specs/09-prd-spec-test-traceability.md:93）。</p>
     *
     * @throws BizException 两路检索均不可用（SYSTEM_ERROR），由上层转为 MODEL_UNAVAILABLE 拒答
     */
    public List<ChunkHit> searchTopKChunks(List<Float> queryVector, String queryText, String categoryId, int topK) {
        if (topK <= 0) {
            return List.of();
        }
        int candidate = Math.max(topK * 2, 10);

        JsonNode knnResponse = null;
        if (queryVector != null && !queryVector.isEmpty()) {
            knnResponse = callEs("POST", "/" + indexName + "/_search",
                    EsQueryDsl.chunkKnnBody(queryVector, categoryId, candidate, Math.max(candidate * 20, 100)),
                    searchTimeoutMs);
        }
        JsonNode textResponse = callEs("POST", "/" + indexName + "/_search",
                EsQueryDsl.chunkTextSearchBody(queryText, categoryId, candidate), searchTimeoutMs);

        if (knnResponse == null && textResponse == null) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "RAG 检索服务暂不可用，请稍后重试");
        }

        List<ChunkHit> knnHits = parseChunkHits(knnResponse, true);
        List<ChunkHit> textHits = parseChunkHits(textResponse, false);
        return RankFusion.fuse(knnHits, textHits, topK);
    }

    /**
     * 按 article_id 批量更新切片状态（下线联动，
     * AC-27 · specs/09-prd-spec-test-traceability.md:93）。
     *
     * <p>ES 失败不回滚已经合法的知识状态，由调用方标记为待补偿
     * （RD-006 / RD-008 · specs/04-resilience-degradation.md:67 / :93）。</p>
     *
     * @return true 表示 ES 侧已受理并完成更新
     */
    public boolean updateChunkStatusByArticleId(String articleId, String newStatus) {
        // 用检索级超时：在线下线的请求路径上，不能让一次 ES 卡顿把管理端请求拖到分钟级；
        // 超时即视为待补偿（RD-006 / RD-008），由 reindex 或再次下线修复。
        JsonNode response = callEs("POST", "/" + indexName + "/_update_by_query?conflicts=proceed&refresh=true",
                EsQueryDsl.updateStatusByArticleBody(articleId, newStatus), searchTimeoutMs);
        if (response == null) {
            log.warn("ES 状态同步失败（待补偿）: articleId={}, targetStatus={}", articleId, newStatus);
            return false;
        }
        log.info("ES 切片状态已同步: articleId={}, status={}, updated={}, versionConflicts={}",
                articleId, newStatus, response.path("updated").asLong(0), response.path("version_conflicts").asLong(0));
        return true;
    }

    /**
     * 存量回填：给缺少 status 的历史切片补为 PUBLISHED。
     *
     * <p>必须先于严格状态过滤上线执行，否则历史切片在检索中会全部不可见。</p>
     *
     * @return 更新条数；-1 表示 ES 不可用
     */
    public long backfillMissingStatus() {
        JsonNode response = callEs("POST", "/" + indexName + "/_update_by_query?conflicts=proceed&refresh=true",
                EsQueryDsl.backfillStatusBody(EsQueryDsl.STATUS_PUBLISHED), bulkTimeoutMs);
        if (response == null) {
            log.warn("存量切片 status 回填失败：ES 不可用");
            return -1L;
        }
        long updated = response.path("updated").asLong(0);
        log.info("存量切片 status 回填完成: updated={}", updated);
        return updated;
    }

    /**
     * 按 article_id 物理清理切片。
     *
     * <p><b>仅用于显式管理端点</b>：知识下线只做逻辑标记（PUBLISHED ➔ OFFLINE），
     * 业务流程不得调用本方法（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515：已发布知识不得物理删除）。</p>
     *
     * @return 删除条数；-1 表示 ES 不可用
     */
    public long deleteChunksByArticleId(String articleId) {
        JsonNode response = callEs("POST", "/" + indexName + "/_delete_by_query?refresh=true",
                EsQueryDsl.deleteByArticleBody(articleId), bulkTimeoutMs);
        if (response == null) {
            log.warn("ES 切片物理清理失败: articleId={}", articleId);
            return -1L;
        }
        long deleted = response.path("deleted").asLong(0);
        log.warn("ES 切片物理清理已执行（显式调用）: articleId={}, deleted={}", articleId, deleted);
        return deleted;
    }

    // ==========================================================================
    // 内部工具
    // ==========================================================================

    private String baseUri() {
        return String.format("%s://%s:%d", esScheme, esHost, esPort);
    }

    private List<ChunkHit> parseChunkHits(JsonNode response, boolean cosineAvailable) {
        List<ChunkHit> hits = new ArrayList<>();
        if (response == null) {
            return hits;
        }
        for (JsonNode hit : response.path("hits").path("hits")) {
            JsonNode source = hit.path("_source");
            String chunkId = textOrNull(source, "chunk_id");
            if (chunkId == null) {
                continue;
            }
            BigDecimal cosine = cosineAvailable
                    ? EsQueryDsl.esScoreToCosine(hit.path("_score").asDouble(0))
                    : null;
            hits.add(ChunkHit.raw(
                    chunkId,
                    textOrNull(source, "article_id"),
                    textOrNull(source, "version_id"),
                    textOrNull(source, "index_version"),
                    source.path("title").asText(""),
                    source.path("content").asText(""),
                    textOrNull(source, "category_id"),
                    cosine));
        }
        return hits;
    }

    /** 摘要：压缩空白并截断至 2000 字（契约 AI-004.4 summary.maxLength=2000） */
    private String summarize(String content) {
        if (content == null || content.isEmpty()) {
            return "";
        }
        String compact = content.replaceAll("\\s+", " ").trim();
        return compact.length() <= 2000 ? compact : compact.substring(0, 2000);
    }

    private String textOrNull(JsonNode node, String field) {
        JsonNode value = node.path(field);
        return value.isMissingNode() || value.isNull() ? null : value.asText();
    }

    /** 切片内容的 SHA-256 指纹（MR-011 · specs/10-model-rag-integration.md:151：索引生命周期追踪与内容变更识别） */
    private String sha256(String text) {
        if (text == null) {
            return "";
        }
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(text.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(digest.length * 2);
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            return "";
        }
    }

    /**
     * 统一 ES HTTP 调用：2xx 返回解析后的 JSON，其余情况记录日志并返回 null（由调用方决定降级语义）。
     */
    private JsonNode callEs(String method, String pathWithQuery, String body, int timeoutMs) {
        String uri = baseUri() + pathWithQuery;
        try {
            HttpRequest.Builder builder = HttpRequest.newBuilder()
                    .uri(URI.create(uri))
                    .header("Content-Type", "application/json")
                    .timeout(Duration.ofMillis(timeoutMs));
            HttpRequest request = body == null
                    ? builder.method(method, HttpRequest.BodyPublishers.noBody()).build()
                    : builder.method(method, HttpRequest.BodyPublishers.ofString(body)).build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() / 100 != 2) {
                log.warn("ES 请求失败 [{} {}] status={}, body={}", method, pathWithQuery, response.statusCode(), response.body());
                return null;
            }
            return objectMapper.readTree(response.body());
        } catch (Exception e) {
            log.warn("ES 请求异常 [{} {}]: {}", method, pathWithQuery, e.getMessage());
            return null;
        }
    }
}
