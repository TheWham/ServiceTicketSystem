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
 * 1. 领域判定（MR-004：OFFICE_IT / OFF_TOPIC / HIGH_RISK / UNCERTAIN，独立于检索结果）；
 * 2. 问题向量化（复用 Embedding 客户端，1024 维）；
 * 3. ES 混合检索（向量 kNN + BM25 全文，RRF 融合），强制 status=PUBLISHED；
 * 4. 阈值分档与引用校验（AI-008：引用必须指向仍然 PUBLISHED 的知识版本）。
 *
 * <p>大模型生成与对话状态由 AI 客服服务负责，本服务通过 /api/v1/rag/retrievals 交付
 * 检索依据与领域判定。领域外/高风险不做检索，办公 IT 的无命中/不相关命中不强制拒答
 * （允许空引用通用回答），置信度不足与知识冲突仍拒答（AI-001 冷启动修订）。</p>
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
     * @param hits                   融合后的 Top-K 切片
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
     * 执行领域判定 + 检索 + 阈值分档。
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

        // 1) 领域判定（MR-004：独立于生成与检索结果，领域外/高风险不做检索）
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

        // 2) 问题向量化；失败按依赖不可用降级，不退化到无依据回答（RD-006）
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

        // 3) 混合检索（强制 PUBLISHED 过滤，AC-27）
        List<ChunkHit> hits;
        try {
            hits = indexService.searchTopKChunks(vector, trimmed, categoryId, resolveTopK(topK));
        } catch (Exception e) {
            log.warn("RAG 检索失败，按依赖不可用降级: {}", e.getMessage());
            return outcome(domain, true, "检索服务不可用", List.of(), zero(), AiRefusalReason.MODEL_UNAVAILABLE, false);
        }

        // 4) 阈值分档（AI-001：无命中/不相关不强制拒答；置信度不足仍拒答）
        BigDecimal topScore = maxSimilarity(hits);
        boolean reliable;
        AiRefusalReason reason;
        if (hits.isEmpty() || topScore.compareTo(properties.getLowConfidenceThreshold()) < 0) {
            // 无命中或不相关命中：不强制拒答，允许上层给出空引用的通用回答
            reliable = false;
            reason = null;
        } else if (topScore.compareTo(properties.getConfidenceThreshold()) < 0) {
            // 介于下限与阈值之间：置信度不足，仍拒答
            reliable = false;
            reason = AiRefusalReason.LOW_CONFIDENCE;
        } else {
            reliable = true;
            reason = null;
        }
        return outcome(domain, false, null, hits, topScore, reason, reliable);
    }

    /**
     * 组装并校验知识引用（AI-008）。
     *
     * <p>同一文章只保留相似度最高的一条切片；引用前复核文章仍为 PUBLISHED，已下线版本一律丢弃。</p>
     */
    public List<KnowledgeCitation> buildVerifiedCitations(List<ChunkHit> hits) {
        if (hits == null || hits.isEmpty()) {
            return List.of();
        }

        Map<String, ChunkHit> bestPerArticle = new LinkedHashMap<>();
        for (ChunkHit hit : hits) {
            if (hit.articleId() == null || hit.versionId() == null) {
                continue;
            }
            ChunkHit current = bestPerArticle.get(hit.articleId());
            if (current == null || scoreOf(hit).compareTo(scoreOf(current)) > 0) {
                bestPerArticle.put(hit.articleId(), hit);
            }
        }
        if (bestPerArticle.isEmpty()) {
            return List.of();
        }

        Set<String> articleIds = new LinkedHashSet<>(bestPerArticle.keySet());
        Set<String> stillPublished = new LinkedHashSet<>();
        for (KnowledgeArticle article : articleMapper.selectBatchIds(articleIds)) {
            if (article.getStatus() == KnowledgeStatus.PUBLISHED) {
                stillPublished.add(article.getArticleId());
            }
        }

        List<KnowledgeCitation> citations = new ArrayList<>();
        for (Map.Entry<String, ChunkHit> entry : bestPerArticle.entrySet()) {
            if (!stillPublished.contains(entry.getKey())) {
                log.warn("引用校验丢弃非发布状态知识: articleId={}", entry.getKey());
                continue;
            }
            ChunkHit hit = entry.getValue();
            citations.add(new KnowledgeCitation(
                    hit.articleId(),
                    hit.versionId(),
                    titleOf(hit),
                    scoreOf(hit),
                    snippetOf(hit)));
        }
        return citations;
    }

    /** 转为对外检索响应（MR-004：只返回 PUBLISHED 版本，携带 score 与 indexVersion） */
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
                // 可靠命中带引用；无命中/不相关也可通用回答（空引用）
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
