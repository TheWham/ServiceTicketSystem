package com.itticket.rag;

import com.itticket.rag.support.EsQueryDsl;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

/**
 * ES 查询 DSL 组装与相似度换算的单元测试（不依赖 ES 实例）。
 *
 * <p>规范引用（路径相对仓库根目录 docs/）：</p>
 * <ul>
 *   <li>AI-001 · specs/02-ai-api-json-schema.md:14 / AC-27 · specs/09-prd-spec-test-traceability.md:93 ——
 *       所有检索 DSL 强制 status=PUBLISHED 过滤；</li>
 *   <li>AI-004.4 · specs/02-ai-api-json-schema.md:174 —— 文章级检索 collapse 折叠 + cardinality 取文章数；</li>
 *   <li>MR-011 · specs/10-model-rag-integration.md:151 —— 置 OFFLINE 时同步写 offline_at；</li>
 *   <li>MR-001 · specs/10-model-rag-integration.md:34 —— 阈值 0.70 判定依赖 esScoreToCosine 换算
 *       （ES cosine _score = (1+cos)/2）。</li>
 * </ul>
 * ES 查询 DSL 组装与相似度换算的单元测试（不依赖 ES 实例，纯文本契约）。
 * 覆盖约 6 类请求体的关键片段：
 *  1) 文章检索（含强制 PUBLISHED 过滤、文章级 collapse 去重、cardinality 计数）；
 *  2) 空 query 的 match_all 兜底；
 *  3) 向量 KNN 请求体参数透传；
 *  4) 状态更新的 Painless 脚本（OFFLINE 同时落 offline_at）；
 *  5) 迁移期状态回填与按文章删除；
 *  6) ES cosine _score -> [0,1] cosine 相似度的换算与越界钳制。
 */
public class EsQueryDslTest {

    /**
     * 文章检索请求体要点：
     * status=PUBLISHED 强制过滤（下线知识绝不外泄）；collapse=article_id 文章级去重（一文多片只出现一次）；
     * cardinality 聚合用于返回“真正的文章总数”（collapse 之后 hits.total 是切片数，不能直接当文章数）；
     * 分类过滤、标题权重(title^2) 与 from/size 分页都要原样出现。
     */
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

    /** 空白 query 走 match_all；且未指定分类时绝不能出现 category_id 过滤条件 */
    @Test
    public void blankQueryFallsBackToMatchAllWithoutCategoryFilter() {
        String body = EsQueryDsl.articleSearchBody("   ", null, 1, 10);

        Assertions.assertTrue(body.contains("match_all"), body);
        Assertions.assertFalse(body.contains("multi_match"), body);
        // 未指定分类时不得出现分类过滤条件（_source 中的字段名属于投影，不算过滤）
        Assertions.assertFalse(body.contains("\"category_id\":\""), body);
    }

    /** KNN 请求体：向量字段、k、num_candidates 原样透传，且同样强制 PUBLISHED 与分类过滤 */
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

    /** 置 OFFLINE 的 Painless 脚本：除 status 外必须同步落 offline_at（MR-011 审计与复盘用） */
    @Test
    public void updateStatusScriptUsesPainlessParams() {
        String body = EsQueryDsl.updateStatusByArticleBody("art-1", "OFFLINE");

        Assertions.assertTrue(body.contains("\"article_id\":\"art-1\""), body);
        Assertions.assertTrue(body.contains("ctx._source.status = params.status"), body);
        Assertions.assertTrue(body.contains("\"status\":\"OFFLINE\""), body);
        // MR-011：置 OFFLINE 时同时记录 offline_at
        Assertions.assertTrue(body.contains("ctx._source.offline_at = params.now"), body);
        Assertions.assertTrue(body.contains("\"now\":\""), body);
    }

    /** 状态回填：只命中“status 字段不存在”的历史文档（must_not exists），并写入目标状态参数 */
    @Test
    public void backfillTargetsDocumentsMissingStatus() {
        String body = EsQueryDsl.backfillStatusBody("PUBLISHED");

        Assertions.assertTrue(body.contains("\"must_not\""), body);
        Assertions.assertTrue(body.contains("\"exists\":{\"field\":\"status\"}"), body);
        Assertions.assertTrue(body.contains("\"params\":{\"status\":\"PUBLISHED\"}"), body);
    }

    /** 按文章删除切片：请求体必须按 article_id 精确删除 */
    @Test
    public void deleteBodyTargetsArticleId() {
        String body = EsQueryDsl.deleteByArticleBody("art-9");

        Assertions.assertTrue(body.contains("\"query\""), body);
        Assertions.assertTrue(body.contains("\"article_id\":\"art-9\""), body);
    }

    /**
     * ES cosine _score -> cosine 相似度换算：ES 返回的 _score = (1 + cos) / 2，
     * 必须反解回 cos 才能沿用业务阈值口径（0.8 等），且越界值钳制到 [0,1]。
     */
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