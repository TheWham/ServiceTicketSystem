package com.itticket.rag;

import com.itticket.common.api.BizException;
import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.dto.ai.KnowledgeCitation;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.enums.AiRefusalReason;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import com.itticket.rag.service.ElasticsearchIndexService;
import com.itticket.rag.service.EmbeddingClientService;
import com.itticket.rag.service.HighRiskGuardrail;
import com.itticket.rag.service.RagRetrievalService;
import com.itticket.rag.vo.ChunkHit;
import com.itticket.rag.vo.RagRetrievalResponse;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.math.BigDecimal;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * 检索与阈值判定测试：覆盖 AI-001 拒答分档、RD-006 依赖降级、AI-008 引用校验。
 */
public class RagRetrievalServiceTest {

    private final ElasticsearchIndexService indexService = Mockito.mock(ElasticsearchIndexService.class);
    private final EmbeddingClientService embeddingService = Mockito.mock(EmbeddingClientService.class);
    private final KnowledgeArticleMapper articleMapper = Mockito.mock(KnowledgeArticleMapper.class);
    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private final HighRiskGuardrail guardrail = new HighRiskGuardrail(properties);

    private final RagRetrievalService service =
            new RagRetrievalService(embeddingService, indexService, guardrail, properties, articleMapper);

    private void stubEmbeddingOk() {
        Mockito.when(embeddingService.generateEmbeddings(anyList()))
                .thenReturn(EmbeddingClientService.EmbeddingResult.builder()
                        .vectors(List.of(List.of(0.1f, 0.2f)))
                        .dimensions(1024)
                        .model("test-embedding")
                        .totalTokens(10)
                        .batchCount(1)
                        .build());
    }

    private void stubSearch(List<ChunkHit> hits) {
        Mockito.when(indexService.searchTopKChunks(anyList(), anyString(), any(), anyInt())).thenReturn(hits);
    }

    private ChunkHit hit(String chunkId, String articleId, String cosine) {
        return ChunkHit.raw(chunkId, articleId, "ver-" + articleId, "网络排查", "正文内容", "C_NET",
                new BigDecimal(cosine));
    }

    private KnowledgeArticle article(String articleId, KnowledgeStatus status) {
        KnowledgeArticle entity = new KnowledgeArticle();
        entity.setArticleId(articleId);
        entity.setStatus(status);
        return entity;
    }

    @Test
    public void reliableWhenSimilarityReachesThreshold() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.8200")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertTrue(outcome.reliable());
        Assertions.assertNull(outcome.suggestedRefusalReason());
        Assertions.assertEquals(new BigDecimal("0.8200"), outcome.topSimilarity());
    }

    @Test
    public void lowConfidenceBetweenThresholds() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.5500")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertFalse(outcome.reliable());
        Assertions.assertEquals(AiRefusalReason.LOW_CONFIDENCE, outcome.suggestedRefusalReason());
    }

    @Test
    public void noReliableKnowledgeBelowLowThreshold() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.2000")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertEquals(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, outcome.suggestedRefusalReason());
    }

    @Test
    public void noReliableKnowledgeWhenNothingRetrieved() {
        stubEmbeddingOk();
        stubSearch(List.of());

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("完全无关的问题", null, null);

        Assertions.assertEquals(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, outcome.suggestedRefusalReason());
        Assertions.assertFalse(outcome.reliable());
    }

    @Test
    public void embeddingFailureDegradesToModelUnavailable() {
        Mockito.when(embeddingService.generateEmbeddings(anyList()))
                .thenThrow(new BizException(com.itticket.common.api.ErrorCode.SYSTEM_ERROR, "向量服务不可用"));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertTrue(outcome.dependencyUnavailable());
        Assertions.assertEquals(AiRefusalReason.MODEL_UNAVAILABLE, outcome.suggestedRefusalReason());
        verifyNoInteractions(indexService);
    }

    @Test
    public void highRiskTopicShortCircuitsBeforeAnyRetrieval() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("我要重置管理员密码", null, null);

        Assertions.assertTrue(outcome.highRiskBlocked());
        Assertions.assertEquals(AiRefusalReason.HIGH_RISK_TOPIC, outcome.suggestedRefusalReason());
        verifyNoInteractions(embeddingService, indexService);
    }

    @Test
    public void blankQuestionIsRejected() {
        Assertions.assertThrows(BizException.class, () -> service.retrieve("   ", null, null));
    }

    @Test
    public void citationsDedupeByArticleAndDropNonPublishedVersions() {
        Mockito.when(articleMapper.selectBatchIds(any())).thenReturn(List.of(
                article("a1", KnowledgeStatus.PUBLISHED),
                article("a2", KnowledgeStatus.OFFLINE)));

        List<KnowledgeCitation> citations = service.buildVerifiedCitations(List.of(
                hit("c1", "a1", "0.9000"),
                hit("c2", "a1", "0.7000"),
                hit("c3", "a2", "0.8000")));

        Assertions.assertEquals(1, citations.size(), "同一文章只保留一条，已下线文章必须被丢弃");
        Assertions.assertEquals("a1", citations.get(0).articleId());
        Assertions.assertEquals(new BigDecimal("0.9000"), citations.get(0).score());
    }

    @Test
    public void citationSnippetIsTruncatedToConfiguredLength() {
        Mockito.when(articleMapper.selectBatchIds(any())).thenReturn(
                List.of(article("a1", KnowledgeStatus.PUBLISHED)));

        String longContent = "排查步骤".repeat(500);
        ChunkHit longHit = ChunkHit.raw("c1", "a1", "ver-a1", "", longContent, "C_NET", new BigDecimal("0.8800"));

        List<KnowledgeCitation> citations = service.buildVerifiedCitations(List.of(longHit));

        Assertions.assertEquals(1, citations.size());
        Assertions.assertEquals(properties.getSnippetLength().intValue(), citations.get(0).snippet().length());
        Assertions.assertFalse(citations.get(0).title().isBlank(), "标题缺失时应退化为正文片段");
    }

    @Test
    public void toResponseMapsHitsAndKeepsPublishedOnlyFlag() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.8200")));

        RagRetrievalResponse response = service.toResponse(service.retrieve("VPN 连不上怎么办", null, null));

        Assertions.assertEquals(1, response.items().size());
        Assertions.assertEquals("c1", response.items().get(0).chunkId());
        Assertions.assertTrue(response.publishedOnly());
        Assertions.assertTrue(response.reliable());
    }

    @Test
    public void topKIsClampedToConfiguredMaximum() {
        stubEmbeddingOk();
        Mockito.when(indexService.searchTopKChunks(anyList(), anyString(), any(), anyInt())).thenReturn(List.of());

        service.retrieve("VPN 连不上怎么办", "C_NET", 999);

        Mockito.verify(indexService).searchTopKChunks(anyList(), anyString(), eq("C_NET"),
                eq(properties.getMaxTopK()));
    }
}
