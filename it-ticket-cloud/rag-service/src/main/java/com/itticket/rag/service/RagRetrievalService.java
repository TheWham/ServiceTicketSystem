package com.itticket.rag.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.dto.ai.KnowledgeCitation;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.enums.AiRefusalReason;
import com.itticket.rag.enums.KnowledgeStatus;
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
 * 1. 问题向量化（复用 Embedding 客户端，1024 维）；
 * 2. ES 混合检索（向量 kNN + BM25 全文，RRF 融合），强制 status=PUBLISHED；
 * 3. 策略判定：高风险词表拦截（HIGH_RISK_TOPIC）、相似度阈值分档（NO_RELIABLE_KNOWLEDGE / LOW_CONFIDENCE）；
 * 4. 引用组装与校验（AI-008：引用必须指向仍然 PUBLISHED 的知识版本）。
 *
 * <p>大模型生成与对话状态由 AI 客服服务负责，本服务通过 /api/v1/rag/retrievals 与
 * /api/v1/consultations/{id}/ai-messages 两个出口把上述结果交给对接方。</p>
 *
 * 【契约依据】AI-001（能力边界与拒答）、AI-008（输出校验）、RD-006（依赖降级）、AC-27（下线不返回）。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RagRetrievalService {

    private final EmbeddingClientService embeddingService;
    private final ElasticsearchIndexService indexService;
    private final HighRiskGuardrail guardrail;
    private final RagRetrievalProperties properties;
    private final KnowledgeArticleMapper articleMapper;

    /**
     * 检索与策略判定结果。
     *
     * @param highRiskBlocked        是否命中高风险主题（命中则不检索、不建议生成）
     * @param matchedKeyword         命中的高风险关键词
     * @param dependencyUnavailable 向量或检索依赖不可用（RD-006：不得用常识补写）
     * @param failureReason         依赖不可用原因（不含内部堆栈）
     * @param hits                  融合后的 Top-K 切片
     * @param topSimilarity         命中的最高余弦相似度
     * @param suggestedRefusalReason 建议拒答原因；为 null 表示达到可靠命中阈值
     */
    public record RetrievalOutcome(
            boolean highRiskBlocked,
            String matchedKeyword,
            boolean dependencyUnavailable,
            String failureReason,
            List<ChunkHit> hits,
            BigDecimal topSimilarity,
            AiRefusalReason suggestedRefusalReason) {

        /** 是否可作为生成回答的依据 */
        public boolean reliable() {
            return !highRiskBlocked && !dependencyUnavailable && suggestedRefusalReason == null;
        }
    }

    /**
     * 执行检索与策略判定。
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

        // 1) 高风险主题：直接拦截，不检索（AI-001）
        HighRiskGuardrail.HighRiskVerdict verdict = guardrail.inspect(trimmed);
        if (verdict.blocked()) {
            return new RetrievalOutcome(true, verdict.matchedKeyword(), false, null, List.of(),
                    BigDecimal.ZERO.setScale(4, RoundingMode.HALF_UP), AiRefusalReason.HIGH_RISK_TOPIC);
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
            return new RetrievalOutcome(false, null, true, "向量服务不可用", List.of(),
                    BigDecimal.ZERO.setScale(4, RoundingMode.HALF_UP), AiRefusalReason.MODEL_UNAVAILABLE);
        }

        // 3) 混合检索（强制 PUBLISHED 过滤）
        List<ChunkHit> hits;
        try {
            hits = indexService.searchTopKChunks(vector, trimmed, categoryId, resolveTopK(topK));
        } catch (Exception e) {
            log.warn("RAG 检索失败，按依赖不可用降级: {}", e.getMessage());
            return new RetrievalOutcome(false, null, true, "检索服务不可用", List.of(),
                    BigDecimal.ZERO.setScale(4, RoundingMode.HALF_UP), AiRefusalReason.MODEL_UNAVAILABLE);
        }

        BigDecimal topSimilarity = maxSimilarity(hits);
        return new RetrievalOutcome(false, null, false, null, hits, topSimilarity,
                judge(topSimilarity, hits.isEmpty()));
    }

    /** 阈值分档：无命中或低于下限 → 无可靠知识；介于下限与生成阈值之间 → 置信度不足 */
    private AiRefusalReason judge(BigDecimal topSimilarity, boolean empty) {
        if (empty) {
            return AiRefusalReason.NO_RELIABLE_KNOWLEDGE;
        }
        if (topSimilarity == null || topSimilarity.compareTo(properties.getLowConfidenceThreshold()) < 0) {
            return AiRefusalReason.NO_RELIABLE_KNOWLEDGE;
        }
        if (topSimilarity.compareTo(properties.getConfidenceThreshold()) < 0) {
            return AiRefusalReason.LOW_CONFIDENCE;
        }
        return null;
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
            if (current == null || similarityOf(hit).compareTo(similarityOf(current)) > 0) {
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
                    similarityOf(hit),
                    snippetOf(hit)));
        }
        return citations;
    }

    /** 转为对外检索响应 */
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
                        hit.cosineSimilarity()))
                .toList();
        return new RagRetrievalResponse(
                items,
                outcome.topSimilarity(),
                outcome.reliable(),
                outcome.highRiskBlocked(),
                outcome.matchedKeyword(),
                outcome.suggestedRefusalReason(),
                true);
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
            BigDecimal similarity = hit.cosineSimilarity();
            if (similarity != null && (max == null || similarity.compareTo(max) > 0)) {
                max = similarity;
            }
        }
        return max == null ? BigDecimal.ZERO.setScale(4, RoundingMode.HALF_UP) : max;
    }

    private BigDecimal similarityOf(ChunkHit hit) {
        return hit.cosineSimilarity() == null ? BigDecimal.ZERO.setScale(4, RoundingMode.HALF_UP) : hit.cosineSimilarity();
    }

    /** 标题非空（契约 citation.title.minLength=1）；缺失时退化为正文前 30 字 */
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
