package com.itticket.rag;

import com.itticket.common.api.BizException;
import com.itticket.rag.config.RagRetrievalProperties;
import com.itticket.rag.dto.ai.KnowledgeCitation;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.enums.AiRefusalReason;
import com.itticket.rag.enums.AiReplyType;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.enums.OfficeDomain;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import com.itticket.rag.service.DomainClassifier;
import com.itticket.rag.service.ElasticsearchIndexService;
import com.itticket.rag.service.EmbeddingClientService;
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
 * 检索与领域判定测试：覆盖 MR-004 领域四态、AI-001（冷启动修订）拒答口径、
 * RD-006 依赖降级、AI-008 引用校验。
 */
public class RagRetrievalServiceTest {

    private final ElasticsearchIndexService indexService = Mockito.mock(ElasticsearchIndexService.class);
    private final EmbeddingClientService embeddingService = Mockito.mock(EmbeddingClientService.class);
    private final KnowledgeArticleMapper articleMapper = Mockito.mock(KnowledgeArticleMapper.class);
    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private final DomainClassifier domainClassifier = new DomainClassifier(properties);

    private final RagRetrievalService service =
            new RagRetrievalService(embeddingService, indexService, domainClassifier, properties, articleMapper);

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

    private ChunkHit hit(String chunkId, String articleId, String score) {
        return ChunkHit.raw(chunkId, articleId, "ver-" + articleId, "ver-" + articleId, "网络排查", "正文内容",
                "C_NET", new BigDecimal(score));
    }

    private KnowledgeArticle article(String articleId, KnowledgeStatus status) {
        KnowledgeArticle entity = new KnowledgeArticle();
        entity.setArticleId(articleId);
        entity.setStatus(status);
        return entity;
    }

    // ------------------------------------------------------------ 阈值分档

    @Test
    public void reliableWhenSimilarityReachesThreshold() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.8200")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertEquals(OfficeDomain.OFFICE_IT, outcome.domain());
        Assertions.assertTrue(outcome.reliable());
        Assertions.assertNull(outcome.suggestedRefusalReason());
        Assertions.assertEquals(new BigDecimal("0.8200"), outcome.topScore());
    }

    @Test
    public void lowConfidenceBetweenThresholds() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.5500")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertFalse(outcome.reliable());
        Assertions.assertEquals(AiRefusalReason.LOW_CONFIDENCE, outcome.suggestedRefusalReason(),
                "置信度不足仍拒答（AI-001）");
    }

    @Test
    public void irrelevantHitDoesNotForceRefusal() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.2000")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertFalse(outcome.reliable());
        Assertions.assertNull(outcome.suggestedRefusalReason(),
                "不相关命中不强制拒答，允许上层给出空引用的通用回答（AI-001 冷启动修订）");
    }

    @Test
    public void emptyHitsDoNotForceRefusal() {
        stubEmbeddingOk();
        stubSearch(List.of());

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("完全无关的问题", null, null);

        Assertions.assertFalse(outcome.reliable());
        Assertions.assertNull(outcome.suggestedRefusalReason(), "无命中不强制拒答（AI-001 冷启动修订）");
    }

    // ------------------------------------------------------------ 依赖降级

    @Test
    public void embeddingFailureDegradesToModelUnavailable() {
        Mockito.when(embeddingService.generateEmbeddings(anyList()))
                .thenThrow(new BizException(com.itticket.common.api.ErrorCode.SYSTEM_ERROR, "向量服务不可用"));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertTrue(outcome.dependencyUnavailable());
        Assertions.assertEquals(AiRefusalReason.MODEL_UNAVAILABLE, outcome.suggestedRefusalReason());
        verifyNoInteractions(indexService);
    }

    // ------------------------------------------------------------ 领域判定（MR-004）

    @Test
    public void highRiskTopicShortCircuitsBeforeRetrieval() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("我要重置管理员密码", null, null);

        Assertions.assertEquals(OfficeDomain.HIGH_RISK, outcome.domain());
        Assertions.assertEquals(AiRefusalReason.HIGH_RISK_TOPIC, outcome.suggestedRefusalReason());
        verifyNoInteractions(embeddingService, indexService);
    }

    @Test
    public void offTopicQuestionRefusedWithoutRetrieval() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("帮我写一份周报", null, null);

        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, outcome.domain());
        Assertions.assertEquals(AiRefusalReason.OFF_TOPIC, outcome.suggestedRefusalReason());
        verifyNoInteractions(embeddingService, indexService);
    }

    @Test
    public void ordinaryAccountIssueIsOfficeItNotHighRisk() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.8200")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("账号登录失败怎么办", null, null);

        Assertions.assertEquals(OfficeDomain.OFFICE_IT, outcome.domain(),
                "普通登录排障不能因含「账号」被误拦（AI-001）");
        Assertions.assertNull(outcome.suggestedRefusalReason());
    }

    @Test
    public void vagueQuestionIsUncertainAndSkipsRetrieval() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("你好", null, null);

        Assertions.assertEquals(OfficeDomain.UNCERTAIN, outcome.domain());
        verifyNoInteractions(embeddingService, indexService);
    }

    // ------------------------------------------------------------ 引用校验

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
        ChunkHit longHit = ChunkHit.raw("c1", "a1", "ver-a1", "ver-a1", "", longContent, "C_NET",
                new BigDecimal("0.8800"));

        List<KnowledgeCitation> citations = service.buildVerifiedCitations(List.of(longHit));

        Assertions.assertEquals(1, citations.size());
        Assertions.assertEquals(properties.getSnippetLength().intValue(), citations.get(0).snippet().length());
        Assertions.assertFalse(citations.get(0).title().isBlank(), "标题缺失时应退化为正文片段");
    }

    // ------------------------------------------------------------ 响应形态

    @Test
    public void toResponseMapsHitsWithDomainScoreAndIndexVersion() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.8200")));

        RagRetrievalResponse response = service.toResponse(service.retrieve("VPN 连不上怎么办", null, null));

        Assertions.assertEquals(1, response.items().size());
        RetrievedChunkAssertions.assertChunk(response.items().get(0), "c1", "a1", "ver-a1", "ver-a1");
        Assertions.assertEquals(OfficeDomain.OFFICE_IT, response.domain());
        Assertions.assertEquals(AiReplyType.ANSWER, response.suggestedReplyType());
        Assertions.assertTrue(response.publishedOnly());
        Assertions.assertTrue(response.reliable());
        Assertions.assertNull(response.suggestedRefusalReason());
    }

    @Test
    public void topKIsClampedToConfiguredMaximum() {
        stubEmbeddingOk();
        Mockito.when(indexService.searchTopKChunks(anyList(), anyString(), any(), anyInt())).thenReturn(List.of());

        service.retrieve("VPN 连不上怎么办", "C_NET", 999);

        Mockito.verify(indexService).searchTopKChunks(anyList(), anyString(), eq("C_NET"),
                eq(properties.getMaxTopK()));
    }

    @Test
    public void blankQuestionIsRejected() {
        Assertions.assertThrows(BizException.class, () -> service.retrieve("   ", null, null));
    }

    /** 本地断言辅助，避免过度暴露 RetrievedChunk 的字段细节 */
    private static final class RetrievedChunkAssertions {
        static void assertChunk(com.itticket.rag.vo.RetrievedChunk chunk, String chunkId,
                                String articleId, String versionId, String indexVersion) {
            Assertions.assertEquals(chunkId, chunk.chunkId());
            Assertions.assertEquals(articleId, chunk.articleId());
            Assertions.assertEquals(versionId, chunk.versionId());
            Assertions.assertEquals(indexVersion, chunk.indexVersion());
            Assertions.assertNotNull(chunk.score());
        }
    }
}
