package com.itticket.rag;

import com.itticket.rag.support.EsQueryDsl;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

/**
 * ES 查询 DSL 组装与相似度换算的单元测试（不依赖 ES 实例）。
 */
public class EsQueryDslTest {

    @Test
    public void articleSearchForcesPublishedFilterAndCollapse() {
        String body = EsQueryDsl.articleSearchBody("VPN 连接失败", "C_NET", 2, 10);

        // AC-27 / AI-001：强制状态过滤
        Assertions.assertTrue(body.contains("\"status\":\"PUBLISHED\""), body);
        // 文章级折叠去重
        Assertions.assertTrue(body.contains("\"collapse\":{\"field\":\"article_id\"}"), body);
        // 文章数用 cardinality 聚合（collapse 后 hits.total 是切片数）
        Assertions.assertTrue(body.contains("\"article_count\""), body);
        Assertions.assertTrue(body.contains("\"cardinality\""), body);
        // 分页
        Assertions.assertTrue(body.contains("\"from\":10"), body);
        Assertions.assertTrue(body.contains("\"size\":10"), body);
        // 分类过滤与标题加权
        Assertions.assertTrue(body.contains("\"category_id\":\"C_NET\""), body);
        Assertions.assertTrue(body.contains("title^2"), body);
    }

    @Test
    public void blankQueryFallsBackToMatchAllWithoutCategoryFilter() {
        String body = EsQueryDsl.articleSearchBody("   ", null, 1, 10);

        Assertions.assertTrue(body.contains("match_all"), body);
        Assertions.assertFalse(body.contains("multi_match"), body);
        // 未指定分类时不得出现分类过滤条件（_source 中的字段名属于投影，不算过滤）
        Assertions.assertFalse(body.contains("\"category_id\":\""), body);
    }

    @Test
    public void knnBodyCarriesVectorAndPublishedFilter() {
        String body = EsQueryDsl.chunkKnnBody(List.of(0.1f, 0.2f, 0.3f), "C_SW", 5, 100);

        Assertions.assertTrue(body.contains("\"field\":\"vector\""), body);
        Assertions.assertTrue(body.contains("\"query_vector\":[0.1,0.2,0.3]"), body);
        Assertions.assertTrue(body.contains("\"k\":5"), body);
        Assertions.assertTrue(body.contains("\"num_candidates\":100"), body);
        Assertions.assertTrue(body.contains("\"status\":\"PUBLISHED\""), body);
        Assertions.assertTrue(body.contains("\"category_id\":\"C_SW\""), body);
    }

    @Test
    public void updateStatusScriptUsesPainlessParams() {
        String body = EsQueryDsl.updateStatusByArticleBody("art-1", "OFFLINE");

        Assertions.assertTrue(body.contains("\"article_id\":\"art-1\""), body);
        Assertions.assertTrue(body.contains("ctx._source.status = params.status"), body);
        Assertions.assertTrue(body.contains("\"params\":{\"status\":\"OFFLINE\"}"), body);
    }

    @Test
    public void backfillTargetsDocumentsMissingStatus() {
        String body = EsQueryDsl.backfillStatusBody("PUBLISHED");

        Assertions.assertTrue(body.contains("\"must_not\""), body);
        Assertions.assertTrue(body.contains("\"exists\":{\"field\":\"status\"}"), body);
        Assertions.assertTrue(body.contains("\"params\":{\"status\":\"PUBLISHED\"}"), body);
    }

    @Test
    public void deleteBodyTargetsArticleId() {
        String body = EsQueryDsl.deleteByArticleBody("art-9");

        Assertions.assertTrue(body.contains("\"query\""), body);
        Assertions.assertTrue(body.contains("\"article_id\":\"art-9\""), body);
    }

    @Test
    public void esScoreIsConvertedBackToCosineSimilarity() {
        // ES 对 cosine 的 _score = (1 + cos) / 2，必须换算否则阈值判定整体偏移
        Assertions.assertEquals(new BigDecimal("1.0000"), EsQueryDsl.esScoreToCosine(1.0d));
        Assertions.assertEquals(new BigDecimal("0.8000"), EsQueryDsl.esScoreToCosine(0.9d));
        Assertions.assertEquals(new BigDecimal("0.3000"), EsQueryDsl.esScoreToCosine(0.65d));
        Assertions.assertEquals(new BigDecimal("0.0000"), EsQueryDsl.esScoreToCosine(0.5d));
        // 越界钳制到 [0,1]
        Assertions.assertEquals(new BigDecimal("0.0000"), EsQueryDsl.esScoreToCosine(0.1d));
        Assertions.assertEquals(new BigDecimal("1.0000"), EsQueryDsl.esScoreToCosine(1.5d));
    }
}
