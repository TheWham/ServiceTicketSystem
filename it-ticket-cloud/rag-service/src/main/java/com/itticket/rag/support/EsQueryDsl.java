package com.itticket.rag.support;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/**
 * ============================================================================
 * Elasticsearch 查询 DSL 组装工具 (EsQueryDsl)
 * ============================================================================
 *
 * 【设计意图】：
 * 纯静态、无状态、不持有 HTTP 连接，便于单元测试直接断言生成的 JSON，
 * 由 ElasticsearchIndexService 负责发送请求。
 *
 * 【契约规范说明】（路径相对仓库根目录 docs/）：
 * 1. AI-001（specs/02-ai-api-json-schema.md:14）/ AC-27（specs/09-prd-spec-test-traceability.md:93）：
 *    所有检索强制过滤 status=PUBLISHED，已下线版本不得返回。
 * 2. 文章级检索响应形态对齐 AI-004.4（specs/02-ai-api-json-schema.md:174）：
 *    按 article_id collapse 去重（切片 → 文章），total 用 cardinality 聚合取文章数，
 *    因为 collapse 后的 hits.total 仍是切片数。
 * 3. 相似度：ES 对 cosine 相似度返回的 _score 为 (1 + cos) / 2，需换算回 [0,1] 区间的余弦相似度，
 *    否则阈值判定（MR-001 · specs/10-model-rag-integration.md:34，默认 0.70）会整体偏移。
 *
 * @author IT工单系统研发组 - RAG专项
 */
public final class EsQueryDsl {

    /** 已发布状态标记；检索白名单只允许该值 */
    public static final String STATUS_PUBLISHED = "PUBLISHED";

    /** ES 深分页上限（from + size） */
    public static final int MAX_WINDOW = 10000;

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private EsQueryDsl() {
    }

    /**
     * 把 ES 的 _score（cosine 时为 (1+cos)/2）换算回 [0,1] 区间的余弦相似度。
     */
    public static BigDecimal esScoreToCosine(double esScore) {
        double cos = 2 * esScore - 1;
        if (cos < 0) {
            cos = 0;
        }
        if (cos > 1) {
            cos = 1;
        }
        return BigDecimal.valueOf(cos).setScale(4, RoundingMode.HALF_UP);
    }

    /**
     * 文章级检索：multi_match(title^2, content) + status 过滤 + article_id collapse + 文章数聚合。
     *
     * @param queryText 关键词；为空时退化为 match_all（仅受状态与分类过滤）
     * @param categoryId 可选分类过滤
     * @param page      页码，从 1 开始
     * @param pageSize  每页文章数
     */
    public static String articleSearchBody(String queryText, String categoryId, int page, int pageSize) {
        ObjectNode root = MAPPER.createObjectNode();
        root.put("from", (page - 1) * pageSize);
        root.put("size", pageSize);
        root.put("track_total_hits", false);
        root.set("query", boolQuery(queryText, categoryId));

        ObjectNode collapse = MAPPER.createObjectNode();
        collapse.put("field", "article_id");
        root.set("collapse", collapse);

        ObjectNode aggs = MAPPER.createObjectNode();
        ObjectNode articleCount = aggs.putObject("article_count");
        ObjectNode cardinality = articleCount.putObject("cardinality");
        cardinality.put("field", "article_id");
        cardinality.put("precision_threshold", 40000);
        root.set("aggs", aggs);

        root.set("_source", sourceFields(true));
        return write(root);
    }

    /**
     * 切片级向量检索（kNN）：强制 status 过滤，供 RAG 问答取 Top-K 依据。
     */
    public static String chunkKnnBody(List<Float> queryVector, String categoryId, int k, int numCandidates) {
        ObjectNode root = MAPPER.createObjectNode();
        root.put("size", k);
        root.set("_source", sourceFields(false));

        ObjectNode knn = root.putObject("knn");
        knn.put("field", "vector");
        ArrayNode vector = knn.putArray("query_vector");
        for (Float v : queryVector) {
            vector.add(v);
        }
        knn.put("k", k);
        knn.put("num_candidates", numCandidates);
        knn.set("filter", filterArray(categoryId));
        return write(root);
    }

    /**
     * 切片级全文检索：与 kNN 路做 RRF 融合，弥补向量召回的精确关键词短板。
     */
    public static String chunkTextSearchBody(String queryText, String categoryId, int size) {
        ObjectNode root = MAPPER.createObjectNode();
        root.put("size", size);
        root.set("_source", sourceFields(false));
        root.set("query", boolQuery(queryText, categoryId));
        return write(root);
    }

    /**
     * 按 article_id 批量更新切片状态（下线联动，AC-27 · specs/09-prd-spec-test-traceability.md:93）；
     * 置 OFFLINE 时同时记录 offline_at（MR-011 · specs/10-model-rag-integration.md:151）
     */
    public static String updateStatusByArticleBody(String articleId, String newStatus) {
        ObjectNode root = MAPPER.createObjectNode();
        ObjectNode term = root.putObject("query").putObject("term");
        term.put("article_id", articleId);

        ObjectNode script = root.putObject("script");
        script.put("lang", "painless");
        script.put("source",
                "ctx._source.status = params.status; "
                        + "if (params.status == 'OFFLINE') { ctx._source.offline_at = params.now; }");
        ObjectNode params = script.putObject("params");
        params.put("status", newStatus);
        params.put("now", java.time.LocalDateTime.now().toString());
        return write(root);
    }

    /** 存量回填：为缺少 status 字段的历史切片补 PUBLISHED，避免严格过滤后旧数据全部不可见（AI-001 · specs/02-ai-api-json-schema.md:14） */
    public static String backfillStatusBody(String status) {
        ObjectNode root = MAPPER.createObjectNode();
        ArrayNode mustNot = root.putObject("query").putObject("bool").putArray("must_not");
        mustNot.addObject().putObject("exists").put("field", "status");

        ObjectNode script = root.putObject("script");
        script.put("lang", "painless");
        script.put("source", "ctx._source.status = params.status");
        script.putObject("params").put("status", status);
        return write(root);
    }

    /** 按 article_id 物理清理切片（仅显式管理端点使用，业务链路不得调用；PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515） */
    public static String deleteByArticleBody(String articleId) {
        ObjectNode root = MAPPER.createObjectNode();
        root.putObject("query").putObject("term").put("article_id", articleId);
        return write(root);
    }

    // ---------------------------------------------------------------- 内部组装

    private static ObjectNode boolQuery(String queryText, String categoryId) {
        ObjectNode bool = MAPPER.createObjectNode();

        ArrayNode must = bool.putArray("must");
        if (queryText == null || queryText.isBlank()) {
            must.addObject().set("match_all", MAPPER.createObjectNode());
        } else {
            ObjectNode multiMatch = must.addObject().putObject("multi_match");
            multiMatch.put("query", queryText);
            ArrayNode fields = multiMatch.putArray("fields");
            fields.add("title^2");
            fields.add("content");
            multiMatch.put("type", "best_fields");
        }

        bool.set("filter", filterArray(categoryId));
        return bool;
    }

    /** 强制状态过滤；categoryId 非空时追加分类过滤 */
    private static ArrayNode filterArray(String categoryId) {
        ArrayNode filters = MAPPER.createArrayNode();
        filters.addObject().putObject("term").put("status", STATUS_PUBLISHED);
        if (categoryId != null && !categoryId.isBlank()) {
            filters.addObject().putObject("term").put("category_id", categoryId);
        }
        return filters;
    }

    private static ArrayNode sourceFields(boolean forArticle) {
        ArrayNode source = MAPPER.createArrayNode();
        if (forArticle) {
            source.add("article_id");
            source.add("version_id");
            source.add("title");
            source.add("category_id");
            source.add("content");
            source.add("published_at");
        } else {
            source.add("chunk_id");
            source.add("article_id");
            source.add("version_id");
            source.add("index_version");
            source.add("title");
            source.add("content");
            source.add("category_id");
            source.add("published_at");
        }
        return source;
    }

    private static String write(ObjectNode node) {
        try {
            return MAPPER.writeValueAsString(node);
        } catch (Exception e) {
            throw new IllegalStateException("ES 查询 DSL 序列化失败: " + e.getMessage(), e);
        }
    }
}
