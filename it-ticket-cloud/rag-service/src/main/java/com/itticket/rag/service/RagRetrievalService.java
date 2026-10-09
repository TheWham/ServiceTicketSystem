package com.itticket.rag.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.dto.ai.KnowledgeCitation;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.enums.AiRefusalReason;
import com.itticket.rag.enums.AiReplyType;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.enums.OfficeDomain;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import com.itticket.rag.vo.ChunkHit;
import com.itticket.rag.vo.RagRetrievalResponse;
import com.itticket.rag.vo.RetrievedChunk;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * ============================================================================
 * RAG 检索与知识策略服务 (RagRetrievalService)
 * ============================================================================
 *
 * 【职责边界】：
 * 本服务负责「把问题变成已发布知识的可靠依据」，不负责生成回答：
 * 1. 领域判定（MR-004 · specs/10-model-rag-integration.md:70：
 *    OFFICE_IT / OFF_TOPIC / HIGH_RISK / UNCERTAIN，独立于检索结果）；
 * 2. 问题向量化（复用 Embedding 客户端，1024 维）；
 * 3. ES 混合检索（向量 kNN + BM25 全文，RRF 融合），强制 status=PUBLISHED
 *    （AI-001 · specs/02-ai-api-json-schema.md:14；AC-27 · specs/09-prd-spec-test-traceability.md:93）；
 * 4. 引用质量阈值与引用校验（AI-008 · specs/02-ai-api-json-schema.md:96：
 *    引用必须指向仍然 PUBLISHED 的知识版本）。
 *
 * <p>大模型生成与对话状态由 AI 客服服务负责，本服务通过 /api/v1/rag/retrievals 交付
 * 检索依据与领域判定。领域外/高风险不做检索，办公 IT 的无命中/弱命中不强制拒答
 * （允许空引用通用回答），相似度仅决定引用质量，知识冲突仍拒答（AI-001，
 * 对应 PRD AC-02 · IT服务工单系统PRD-Ultimate.md:886）。</p>
 *
 * 【降级语义】：
 * 向量或检索依赖不可用时按 RD-006（specs/04-resilience-degradation.md:67）返回
 * dependencyUnavailable + MODEL_UNAVAILABLE，不得用模型常识补写回答；
 * 依赖超时边界按 RD-003（specs/04-resilience-degradation.md:33）。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RagRetrievalService {

    private final EmbeddingClientService embeddingService;
    private final ElasticsearchIndexService indexService;
    private final DomainClassifier domainClassifier;
    private final RagRetrievalProperties properties;
    private final KnowledgeArticleMapper articleMapper;

    /**
     * 检索与策略判定结果。
     *
     * @param domain                 MR-004 领域判定（独立于生成结果）
     * @param dependencyUnavailable  向量或检索依赖不可用（RD-006：不得用常识补写）
     * @param failureReason          依赖不可用原因（不含内部堆栈）
     * @param hits                   融合后经已发布当前版本校验的 Top-K 切片
     * @param topScore               命中最高余弦相似度
     * @param suggestedRefusalReason 建议拒答原因；为 null 表示不拒答
     * @param reliable               是否达到可靠命中阈值（可据此生成带引用的回答）
     */
    public record RetrievalOutcome(
            OfficeDomain domain,
            boolean dependencyUnavailable,
            String failureReason,
            List<ChunkHit> hits,
            BigDecimal topScore,
            AiRefusalReason suggestedRefusalReason,
            boolean reliable) {

        /** 命中领域外（必须拒答） */
        public boolean isOffTopic() {
            return domain == OfficeDomain.OFF_TOPIC;
        }

        /** 命中高风险主题（必须拒答并提供人工入口） */
        public boolean isHighRisk() {
            return domain == OfficeDomain.HIGH_RISK;
        }

        /** 语义不明确（应追问澄清，不生成回答） */
        public boolean isUncertain() {
            return domain == OfficeDomain.UNCERTAIN;
        }
    }

    /**
     * 执行领域判定 + 检索 + 引用质量判定。
     *
     * @param question   用户问题
     * @param categoryId 可选分类过滤
     * @param topK       返回条数；为空取配置默认值
     */
    public RetrievalOutcome retrieve(String question, String categoryId, Integer topK) {
        if (question == null || question.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "question 不能为空");
        }
        String trimmed = question.trim();

        // 1) 领域判定（MR-004 · specs/10-model-rag-integration.md:70：
        //    独立于生成与检索结果，领域外/高风险不做检索）
        DomainClassifier.Verdict verdict = domainClassifier.classify(trimmed);
        OfficeDomain domain = verdict.domain();
        if (domain == OfficeDomain.OFF_TOPIC) {
            log.info("问题判定为领域外，拒绝检索与回答: rule={}", verdict.matchedRule());
            return outcome(domain, false, null, List.of(), zero(), AiRefusalReason.OFF_TOPIC, false);
        }
        if (domain == OfficeDomain.HIGH_RISK) {
            log.info("问题命中高风险主题，拒绝检索与回答: rule={}", verdict.matchedRule());
            return outcome(domain, false, null, List.of(), zero(), AiRefusalReason.HIGH_RISK_TOPIC, false);
        }
        if (domain == OfficeDomain.UNCERTAIN) {
            // 语义不清：上层应 CLARIFY，不做检索与回答
            return outcome(domain, false, null, List.of(), zero(), null, false);
        }

        // 2) 问题向量化；失败按依赖不可用降级，不退化到无依据回答（RD-006 · specs/04-resilience-degradation.md:67）
        List<Float> vector;
        try {
            EmbeddingClientService.EmbeddingResult embedding = embeddingService.generateEmbeddings(List.of(trimmed));
            if (embedding.getVectors() == null || embedding.getVectors().isEmpty()) {
                throw new IllegalStateException("向量化未返回结果");
            }
            vector = embedding.getVectors().get(0);
        } catch (Exception e) {
            log.warn("RAG 向量化失败，按依赖不可用降级: {}", e.getMessage());
            return outcome(domain, true, "向量服务不可用", List.of(), zero(), AiRefusalReason.MODEL_UNAVAILABLE, false);
        }

        // 3) 混合检索（强制 PUBLISHED 过滤：AI-001 · specs/02-ai-api-json-schema.md:14；
        //    AC-27 · specs/09-prd-spec-test-traceability.md:93）
        List<ChunkHit> hits;
        try {
            hits = indexService.searchTopKChunks(vector, trimmed, categoryId, resolveTopK(topK));
        } catch (Exception e) {
            log.warn("RAG 检索失败，按依赖不可用降级: {}", e.getMessage());
            return outcome(domain, true, "检索服务不可用", List.of(), zero(), AiRefusalReason.MODEL_UNAVAILABLE, false);
        }

        // 4) ES 可能尚未同步下线/版本切换，先按数据库当前发布版本过滤，
        //    避免旧版本进入生成上下文或抬高可靠性评分。
        try {
            hits = filterPublishedCurrentHits(hits);
        } catch (BizException e) {
            return outcome(domain, true, "知识状态校验服务不可用", List.of(), zero(),
                    AiRefusalReason.MODEL_UNAVAILABLE, false);
        }

        // 5) 相似度只决定引用质量；无命中或弱命中允许上层使用模型通用能力。
        //    lowConfidenceThreshold 仅保留配置兼容，不参与可靠性或拒答判定。
        BigDecimal topScore = maxSimilarity(hits);
        boolean reliable = !hits.isEmpty() && topScore.compareTo(properties.getConfidenceThreshold()) >= 0;
        return outcome(domain, false, null, hits, topScore, null, reliable);
    }

    /**
     * 组装并校验知识引用（AI-008 · specs/02-ai-api-json-schema.md:96）。
     *
     * <p>先复核文章仍为 PUBLISHED 且切片属于 currentVersionId，再为同一文章保留最高分切片；
     * 已下线及历史版本一律丢弃
     * （AC-27 · specs/09-prd-spec-test-traceability.md:93）。</p>
     *
     * @throws BizException 状态校验依赖不可用，不能伪装为空引用
     */
    public List<KnowledgeCitation> buildVerifiedCitations(List<ChunkHit> hits) {
        if (hits == null || hits.isEmpty()) {
            return List.of();
        }

        Map<String, ChunkHit> bestPerArticle = new LinkedHashMap<>();
        for (ChunkHit hit : filterPublishedCurrentHits(hits)) {
            ChunkHit current = bestPerArticle.get(hit.articleId());
            if (current == null || scoreOf(hit).compareTo(scoreOf(current)) > 0) {
                bestPerArticle.put(hit.articleId(), hit);
            }
        }
        List<KnowledgeCitation> citations = new ArrayList<>();
        for (ChunkHit hit : bestPerArticle.values()) {
            citations.add(new KnowledgeCitation(
                    hit.articleId(),
                    hit.versionId(),
                    titleOf(hit),
                    scoreOf(hit),
                    snippetOf(hit)));
        }
        return citations;
    }

    /** 批量复核当前发布版本，保留检索顺序及同一文章的多个有效切片。 */
    private List<ChunkHit> filterPublishedCurrentHits(List<ChunkHit> hits) {
        if (hits == null || hits.isEmpty()) {
            return List.of();
        }
        List<ChunkHit> candidates = hits.stream()
                .filter(hit -> hit != null && hit.articleId() != null && !hit.articleId().isBlank()
                        && hit.versionId() != null && !hit.versionId().isBlank())
                .toList();
        Set<String> articleIds = new LinkedHashSet<>();
        for (ChunkHit hit : candidates) {
            articleIds.add(hit.articleId());
        }
        if (articleIds.isEmpty()) {
            return List.of();
        }

        List<KnowledgeArticle> articles;
        try {
            articles = articleMapper.selectBatchIds(articleIds);
        } catch (RuntimeException e) {
            log.warn("RAG 知识状态校验失败，按依赖不可用处理", e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "知识状态校验服务不可用");
        }
        Map<String, String> publishedVersions = new LinkedHashMap<>();
        for (KnowledgeArticle article : articles) {
            if (article.getStatus() == KnowledgeStatus.PUBLISHED && article.getCurrentVersionId() != null) {
                publishedVersions.put(article.getArticleId(), article.getCurrentVersionId());
            }
        }
        return candidates.stream()
                .filter(hit -> hit.versionId().equals(publishedVersions.get(hit.articleId())))
                .toList();
    }

    /** 将 retrieve 已校验的结果转为对外响应，携带引用质量 score 与 indexVersion（MR-004）。 */
    public RagRetrievalResponse toResponse(RetrievalOutcome outcome) {
        List<RetrievedChunk> items = outcome.hits() == null ? List.of() : outcome.hits().stream()
                .map(hit -> new RetrievedChunk(
                        hit.chunkId(),
                        hit.articleId(),
                        hit.versionId(),
                        titleOf(hit),
                        snippetOf(hit),
                        hit.content(),
                        hit.categoryId(),
                        hit.cosineSimilarity(),
                        hit.indexVersion()))
                .toList();
        return new RagRetrievalResponse(
                items,
                outcome.domain(),
                suggestedReplyType(outcome),
                outcome.suggestedRefusalReason(),
                outcome.topScore(),
                outcome.reliable(),
                true);
    }

    /** 建议的回答类型（供 AI 客服服务参考，最终决定权在上层） */
    private AiReplyType suggestedReplyType(RetrievalOutcome outcome) {
        return switch (outcome.domain()) {
            case OFF_TOPIC, HIGH_RISK -> AiReplyType.REFUSE;
            case UNCERTAIN -> AiReplyType.CLARIFY;
            case OFFICE_IT -> {
                if (outcome.dependencyUnavailable() || outcome.suggestedRefusalReason() != null) {
                    yield AiReplyType.REFUSE;
                }
                // 可靠命中带引用；无命中/弱命中也可通用回答（空引用）
                yield AiReplyType.ANSWER;
            }
        };
    }

    private RetrievalOutcome outcome(OfficeDomain domain, boolean dependencyUnavailable, String failureReason,
                                     List<ChunkHit> hits, BigDecimal topScore,
                                     AiRefusalReason refusalReason, boolean reliable) {
        return new RetrievalOutcome(domain, dependencyUnavailable, failureReason,
                hits, topScore, refusalReason, reliable);
    }

    private int resolveTopK(Integer requested) {
        int fallback = properties.getTopK() == null ? 5 : properties.getTopK();
        int topK = requested == null || requested <= 0 ? fallback : requested;
        int max = properties.getMaxTopK() == null ? 20 : properties.getMaxTopK();
        return Math.min(topK, max);
    }

    private BigDecimal maxSimilarity(List<ChunkHit> hits) {
        BigDecimal max = null;
        for (ChunkHit hit : hits) {
            BigDecimal score = hit.cosineSimilarity();
            if (score != null && (max == null || score.compareTo(max) > 0)) {
                max = score;
            }
        }
        return max == null ? zero() : max;
    }

    private BigDecimal scoreOf(ChunkHit hit) {
        return hit.cosineSimilarity() == null ? zero() : hit.cosineSimilarity();
    }

    private static BigDecimal zero() {
        return BigDecimal.ZERO.setScale(4, RoundingMode.HALF_UP);
    }

    /** 标题非空（契约 citation.title.minLength=1）；缺失时退化为正文片段 */
    private String titleOf(ChunkHit hit) {
        String title = hit.title();
        if (title != null && !title.isBlank()) {
            return title.length() > 200 ? title.substring(0, 200) : title;
        }
        String content = hit.content() == null ? "" : hit.content().replaceAll("\\s+", " ").trim();
        if (content.isEmpty()) {
            return "未命名知识片段";
        }
        return content.length() > 30 ? content.substring(0, 30) : content;
    }

    /** 引用片段：压缩空白并截断（契约 citation.snippet 1..1000） */
    private String snippetOf(ChunkHit hit) {
        int limit = properties.getSnippetLength() == null ? 1000 : properties.getSnippetLength();
        String content = hit.content() == null ? "" : hit.content().replaceAll("\\s+", " ").trim();
        if (content.isEmpty()) {
            return titleOf(hit);
        }
        return content.length() <= limit ? content : content.substring(0, limit);
    }
}
