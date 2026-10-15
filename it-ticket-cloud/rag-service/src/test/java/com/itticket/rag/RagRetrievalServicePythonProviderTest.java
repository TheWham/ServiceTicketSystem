package com.itticket.rag;

import com.itticket.common.api.BizException;
import com.itticket.rag.client.PythonRetrievalClient;
import com.itticket.rag.config.RagRetrievalProperties;
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
import com.itticket.rag.vo.RagRetrievalResponse;
import com.itticket.rag.vo.RetrievedChunk;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.math.BigDecimal;
import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * provider=python 分支：RagRetrievalService 把检索内核（②向量化 + ③ES 检索）外包给
 * Python 检索服务后的行为。Java 侧 ① 领域判定与 ④ MySQL PUBLISHED 复核不变；
 * ⑤ 透传 Python 的 reliable/拒答判定，复核滤除后修补 topScore/拒答。
 *
 * <p>ES 旧路径（provider=es，默认）行为由 RagRetrievalServiceTest 覆盖，不在此重复。</p>
 */
public class RagRetrievalServicePythonProviderTest {

    private final ElasticsearchIndexService indexService = Mockito.mock(ElasticsearchIndexService.class);
    private final EmbeddingClientService embeddingService = Mockito.mock(EmbeddingClientService.class);
    private final KnowledgeArticleMapper articleMapper = Mockito.mock(KnowledgeArticleMapper.class);
    private final PythonRetrievalClient pythonClient = Mockito.mock(PythonRetrievalClient.class);
    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private final DomainClassifier domainClassifier = new DomainClassifier(properties);

    {
        properties.setProvider(RagRetrievalProperties.Provider.python);
    }

    private final RagRetrievalService service =
            new RagRetrievalService(embeddingService, indexService, domainClassifier, properties,
                    articleMapper, pythonClient);

    private RetrievedChunk chunk(String chunkId, String articleId, String score) {
        return new RetrievedChunk(chunkId, articleId, "ver-" + articleId, "标题", "片段", "正文内容",
                "C_NET", new BigDecimal(score), "ver-" + articleId);
    }

    private RagRetrievalResponse pyAnswer(List<RetrievedChunk> items, boolean reliable) {
        BigDecimal top = items.stream().map(RetrievedChunk::score).max(BigDecimal::compareTo)
                .orElse(new BigDecimal("0.0"));
        return new RagRetrievalResponse(items, OfficeDomain.OFFICE_IT, AiReplyType.ANSWER, null,
                top, reliable, true);
    }

    private RagRetrievalResponse pyRefuse(AiRefusalReason reason) {
        return new RagRetrievalResponse(List.of(), OfficeDomain.OFFICE_IT, AiReplyType.REFUSE, reason,
                new BigDecimal("0.0"), false, true);
    }

    private KnowledgeArticle published(String articleId) {
        KnowledgeArticle entity = new KnowledgeArticle();
        entity.setArticleId(articleId);
        entity.setStatus(KnowledgeStatus.PUBLISHED);
        entity.setCurrentVersionId("ver-" + articleId);
        return entity;
    }

    /**
     * 透传：Python 判定 reliable=true 时 Java 不再套 0.70 余弦阈值，
     * topScore=max(items.score)；embedding 与 ES 完全不被触碰。
     */
    @Test
    public void pythonProviderPassesThroughReliableAndSkipsEsAndEmbedding() {
        Mockito.when(articleMapper.selectBatchIds(any())).thenReturn(List.of(
                published("a1"), published("a2")));
        Mockito.when(pythonClient.retrieve("VPN 连不上怎么办", null, 5))
                .thenReturn(pyAnswer(List.of(chunk("c1", "a1", "0.8123"), chunk("c2", "a2", "0.7011")), true));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);
        RagRetrievalResponse response = service.toResponse(outcome);

        Assertions.assertEquals(OfficeDomain.OFFICE_IT, outcome.domain());
        Assertions.assertTrue(response.reliable(), "reliable 必须透传 Python 判定，不再套 0.70 阈值");
        Assertions.assertNull(response.suggestedRefusalReason());
        Assertions.assertEquals(AiReplyType.ANSWER, response.suggestedReplyType());
        Assertions.assertEquals(new BigDecimal("0.8123"), response.topScore());
        Assertions.assertEquals(2, response.items().size());
        Assertions.assertEquals("ver-a1", response.items().get(0).indexVersion());
        verifyNoInteractions(embeddingService, indexService);
    }

    /**
     * 部分滤除：④ MySQL 复核丢掉非当前版本命中后，topScore 必须按剩余命中重算，
     * 否则 consultation 侧 topScore==max(items.score) 强校验不通过。
     */
    @Test
    public void pythonProviderRecomputesTopScoreAfterPublishedFilter() {
        Mockito.when(articleMapper.selectBatchIds(any())).thenReturn(List.of(published("a1")));
        Mockito.when(pythonClient.retrieve(anyString(), any(), anyInt()))
                .thenReturn(pyAnswer(List.of(chunk("c1", "a1", "0.9000"), chunk("c2", "a2", "0.8000")), true));

        RagRetrievalResponse response = service.toResponse(service.retrieve("VPN 连不上怎么办", null, null));

        Assertions.assertEquals(1, response.items().size());
        Assertions.assertEquals(new BigDecimal("0.9000"), response.topScore());
        Assertions.assertTrue(response.reliable());
    }

    /**
     * 复核滤空：Python 返回了命中但全部未过 PUBLISHED 复核 →
     * 强制 reliable=false / REFUSE / LOW_CONFIDENCE（保持 ANSWER⇔reliable⇔reason=null 不变量）。
     */
    @Test
    public void pythonProviderFilteredToEmptyRefusesWithLowConfidence() {
        KnowledgeArticle stale = published("a1");
        stale.setCurrentVersionId("ver-other");
        Mockito.when(articleMapper.selectBatchIds(any())).thenReturn(List.of(stale));
        Mockito.when(pythonClient.retrieve(anyString(), any(), anyInt()))
                .thenReturn(pyAnswer(List.of(chunk("c1", "a1", "0.9000")), true));

        RagRetrievalResponse response = service.toResponse(service.retrieve("VPN 连不上怎么办", null, null));

        Assertions.assertTrue(response.items().isEmpty());
        Assertions.assertFalse(response.reliable());
        Assertions.assertEquals(AiReplyType.REFUSE, response.suggestedReplyType());
        Assertions.assertEquals(AiRefusalReason.LOW_CONFIDENCE, response.suggestedRefusalReason());
        Assertions.assertEquals(new BigDecimal("0.0000"), response.topScore());
    }

    /**
     * 拒答透传：Python 判低置信拒答（items 空 + LOW_CONFIDENCE）时，
     * Java 原样透传且不触 MySQL（复核对空列表短路）。
     */
    @Test
    public void pythonProviderRefusalPassthrough() {
        Mockito.when(pythonClient.retrieve(anyString(), any(), anyInt()))
                .thenReturn(pyRefuse(AiRefusalReason.LOW_CONFIDENCE));

        RagRetrievalResponse response = service.toResponse(service.retrieve("VPN 连不上怎么办", null, null));

        Assertions.assertTrue(response.items().isEmpty());
        Assertions.assertFalse(response.reliable());
        Assertions.assertEquals(AiReplyType.REFUSE, response.suggestedReplyType());
        Assertions.assertEquals(AiRefusalReason.LOW_CONFIDENCE, response.suggestedRefusalReason());
        verifyNoInteractions(articleMapper);
        verifyNoInteractions(embeddingService, indexService);
    }

    /**
     * 依赖降级：Python 服务不可达时按 RD-006 走既有失败路径（MODEL_UNAVAILABLE），
     * 不静默回 ES，也不伪装成空引用。
     */
    @Test
    public void pythonProviderFailureDegradesToModelUnavailable() {
        Mockito.when(pythonClient.retrieve(anyString(), any(), anyInt()))
                .thenThrow(new IllegalStateException("Python 检索调用失败: connect refused"));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);
        RagRetrievalResponse response = service.toResponse(outcome);

        Assertions.assertTrue(outcome.dependencyUnavailable());
        Assertions.assertEquals(AiReplyType.REFUSE, response.suggestedReplyType());
        Assertions.assertEquals(AiRefusalReason.MODEL_UNAVAILABLE, response.suggestedRefusalReason());
        Assertions.assertFalse(response.reliable());
        verifyNoInteractions(embeddingService, indexService, articleMapper);
    }

    /**
     * ① 领域判定前置不变：高危主题短路拒答，连 Python 也不调用。
     */
    @Test
    public void pythonProviderStillShortCircuitsHighRisk() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("我要重置管理员密码", null, null);

        Assertions.assertEquals(OfficeDomain.HIGH_RISK, outcome.domain());
        Assertions.assertEquals(AiRefusalReason.HIGH_RISK_TOPIC, outcome.suggestedRefusalReason());
        verifyNoInteractions(pythonClient, embeddingService, indexService, articleMapper);
    }

    /**
     * 契约自洽（评审 Important）：reliable 透传 Python 判定，但重算后的 topScore 必须与之一致。
     * 若复核后幸存的唯一命中分数为 0，consultation 侧 `reliable && topScore.signum() > 0`
     * 强校验会抛 INVALID_RESPONSE 且不重试——必须在此把 reliable 收敛为 false。
     */
    @Test
    public void pythonProviderDropsReliabilityWhenSurvivingScoreIsZero() {
        Mockito.when(articleMapper.selectBatchIds(any())).thenReturn(List.of(published("a1")));
        Mockito.when(pythonClient.retrieve(anyString(), any(), anyInt()))
                .thenReturn(pyAnswer(List.of(chunk("c1", "a1", "0.0000")), true));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);
        RagRetrievalResponse response = service.toResponse(outcome);

        Assertions.assertEquals(new BigDecimal("0.0000"), response.topScore());
        Assertions.assertFalse(response.reliable(),
                "topScore 为 0 时 reliable 必须为 false（consultation 强校验 reliable ⇒ topScore > 0）");
        Assertions.assertNull(response.suggestedRefusalReason());
        Assertions.assertEquals(AiReplyType.ANSWER, response.suggestedReplyType());
    }

    /**
     * 透传语义保持：部分滤除后剩余命中分数较低（如 0.35）时仍透传 Python 的 reliable=true，
     * 不重新引入 0.70 余弦阈值（拒答判定权在 Python 侧，计划已拍板）。
     */
    @Test
    public void pythonProviderKeepsPassthroughReliabilityForLowerScoredSurvivor() {
        Mockito.when(articleMapper.selectBatchIds(any())).thenReturn(List.of(published("a2")));
        Mockito.when(pythonClient.retrieve(anyString(), any(), anyInt()))
                .thenReturn(pyAnswer(List.of(chunk("c1", "a1", "0.9000"), chunk("c2", "a2", "0.3500")), true));

        RagRetrievalResponse response = service.toResponse(service.retrieve("VPN 连不上怎么办", null, null));

        Assertions.assertEquals(1, response.items().size());
        Assertions.assertEquals(new BigDecimal("0.3500"), response.topScore());
        Assertions.assertTrue(response.reliable(), "透传 Python 判定，不套 0.70 阈值");
    }

    /**
     * 配置默认值：provider 默认 es（零代码回滚路径），Python 地址默认 127.0.0.1:8310。
     */
    @Test
    public void esRemainsDefaultProvider() {
        RagRetrievalProperties defaults = new RagRetrievalProperties();
        Assertions.assertEquals(RagRetrievalProperties.Provider.es, defaults.getProvider());
        Assertions.assertEquals("http://127.0.0.1:8310", defaults.getPythonBaseUrl());
        Assertions.assertEquals(4200, defaults.getPythonTimeoutMs().intValue());
    }
}
