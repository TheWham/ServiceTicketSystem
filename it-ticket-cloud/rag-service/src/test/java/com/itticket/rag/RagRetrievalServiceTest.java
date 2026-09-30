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
 *
 * <p>规范引用（路径相对仓库根目录 docs/）：</p>
 * <ul>
 *   <li>MR-004 · specs/10-model-rag-integration.md:70 —— 领域判定前置于检索，领域外/高风险短路；</li>
 *   <li>AI-001 · specs/02-ai-api-json-schema.md:14 —— 阈值分档：≥0.70 可靠、0.45–0.70 拒答
 *       LOW_CONFIDENCE、&lt;0.45 或无命中不强制拒答（冷启动修订，对应 PRD AC-02 · PRD:886）；</li>
 *   <li>RD-006 · specs/04-resilience-degradation.md:67 —— 向量化失败按依赖不可用降级 MODEL_UNAVAILABLE；</li>
 *   <li>AI-008 · specs/02-ai-api-json-schema.md:96 —— 引用复核仍 PUBLISHED，已下线丢弃（AC-27 · specs/09:93）；</li>
 *   <li>AI-004.3 · specs/02-ai-api-json-schema.md:134 —— citation.snippet ≤1000、title 非空。</li>
 * </ul>
 *
 * <p>纯单元测试：Mockito 打桩 Embedding/ES/mapper，不依赖外部服务。</p>
 * 被测对象 RagRetrievalService 是 AI 问答链路的“守门员”，每次提问的处理顺序：
 *   1) 领域判定（DomainClassifier，纯本地规则）：HIGH_RISK / OFF_TOPIC 直接拒答、
 *      UNCERTAIN 反问澄清 —— 这三种“短路”，连 embedding 与 ES 调用都不发生；
 *   2) 向量化 + 双路检索（embedding 服务 + Elasticsearch）；
 *   3) 相似度阈值分档决定 reliable 与 suggestedRefusalReason：
 *      top >= reliable 阈值            -> 可靠回答（可挂引用）；
 *      low <= top < reliable           -> LOW_CONFIDENCE 拒答（有沾边内容但不够可信）；
 *      top < low（冷启动修订口径）      -> 不强制拒答，允许上层给无引用的通用答复；
 *   4) 引用校验建 citations：只保留 PUBLISHED 文章、按文章去重、正文截断。
 * 阈值与依赖全部走 RagRetrievalProperties 注入；本测试用默认配置 + mock 外部调用。
 */
public class RagRetrievalServiceTest {

    private final ElasticsearchIndexService indexService = Mockito.mock(ElasticsearchIndexService.class);
    private final EmbeddingClientService embeddingService = Mockito.mock(EmbeddingClientService.class);
    private final KnowledgeArticleMapper articleMapper = Mockito.mock(KnowledgeArticleMapper.class);
    private final RagRetrievalProperties properties = new RagRetrievalProperties();
    private final DomainClassifier domainClassifier = new DomainClassifier(properties);

    private final RagRetrievalService service =
            new RagRetrievalService(embeddingService, indexService, domainClassifier, properties, articleMapper);

    /**
     * 桩：embedding 服务正常返回一个向量（维度/模型名仅留痕，不参与断言）。
     */
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

    /**
     * 桩：ES 双路检索返回指定命中列表（score 即余弦相似度，决定阈值分档结果）。
     */
    private void stubSearch(List<ChunkHit> hits) {
        Mockito.when(indexService.searchTopKChunks(anyList(), anyString(), any(), anyInt())).thenReturn(hits);
    }

    /**
     * 造一个 KNN 命中的切片：固定挂在“网络排查/C_NET”下，版本号由 articleId 派生，
     * score 为本用例要考察的相似度取值。
     */
    private ChunkHit hit(String chunkId, String articleId, String score) {
        return ChunkHit.raw(chunkId, articleId, "ver-" + articleId, "ver-" + articleId, "网络排查", "正文内容",
                "C_NET", new BigDecimal(score));
    }

    /**
     * 造一个指定发布状态的文章实体，配合 selectBatchIds 模拟引用有效性回查。
     */
    private KnowledgeArticle article(String articleId, KnowledgeStatus status) {
        KnowledgeArticle entity = new KnowledgeArticle();
        entity.setArticleId(articleId);
        entity.setStatus(status);
        return entity;
    }

    // ------------------------------------------------------------ 阈值分档

    /**
     * 阈值上档：top 相似度 0.82 >= reliable 阈值 -> reliable=true、无拒答理由，
     * 领域判定为 OFFICE_IT（普通 VPN 排障）。
     */
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

    /**
     * 阈值中档：0.55 落在 [low, reliable) 之间 -> 强制 LOW_CONFIDENCE 拒答（AI-001），
     * 宁可拒答转人工，也不输出没把握的内容。
     */
    @Test
    public void lowConfidenceBetweenThresholds() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.5500")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertFalse(outcome.reliable());
        Assertions.assertEquals(AiRefusalReason.LOW_CONFIDENCE, outcome.suggestedRefusalReason(),
                "置信度不足仍拒答（AI-001）");
    }

    /**
     * 阈值下档（冷启动修订口径）：top=0.20 属“不相关命中”，不强制拒答 ——
     * 知识库刚起步内容稀疏时，允许上层给不带引用的通用答复，避免用户一上来全是拒答。
     */
    @Test
    public void irrelevantHitDoesNotForceRefusal() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.2000")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("VPN 连不上怎么办", null, null);

        Assertions.assertFalse(outcome.reliable());
        Assertions.assertNull(outcome.suggestedRefusalReason(),
                "不相关命中不强制拒答，允许上层给出空引用的通用回答（AI-001 冷启动修订）");
    }

    /**
     * 零命中：同样不强制拒答（理由同冷启动口径），suggestedRefusalReason 为 null。
     */
    @Test
    public void emptyHitsDoNotForceRefusal() {
        stubEmbeddingOk();
        stubSearch(List.of());

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("完全无关的问题", null, null);

        Assertions.assertFalse(outcome.reliable());
        Assertions.assertNull(outcome.suggestedRefusalReason(), "无命中不强制拒答（AI-001 冷启动修订）");
    }

    // ------------------------------------------------------------ 依赖降级

    /**
     * RD-006 依赖降级：向量化服务故障 -> suggestedRefusalReason=MODEL_UNAVAILABLE，
     * 上层据此走“系统繁忙/转人工”分支，而不是抛 500 或给假答案。
     */
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

    /**
     * 短路红线：高危主题在领域判定阶段直接拒答，
     * verifyNoInteractions 硬断言连 embedding/检索都没有发生（不在危险主题上浪费推理）。
     */
    @Test
    public void highRiskTopicShortCircuitsBeforeRetrieval() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("我要重置管理员密码", null, null);

        Assertions.assertEquals(OfficeDomain.HIGH_RISK, outcome.domain());
        Assertions.assertEquals(AiRefusalReason.HIGH_RISK_TOPIC, outcome.suggestedRefusalReason());
        verifyNoInteractions(embeddingService, indexService);
    }

    /**
     * OFF_TOPIC 同样短路拒答（理由透出给前端展示“非业务范围”），且零检索调用。
     */
    @Test
    public void offTopicQuestionRefusedWithoutRetrieval() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("帮我写一份周报", null, null);

        Assertions.assertEquals(OfficeDomain.OFF_TOPIC, outcome.domain());
        Assertions.assertEquals(AiRefusalReason.OFF_TOPIC, outcome.suggestedRefusalReason());
        verifyNoInteractions(embeddingService, indexService);
    }

    /**
     * 防误拦回归：普通账号登录排障含“账号”关键词，绝不能被归为 HIGH_RISK ——
     * 误拦的伤害大于漏拦（正常用户被拒之门外），该用例守住分类器的关键边界。
     */
    @Test
    public void ordinaryAccountIssueIsOfficeItNotHighRisk() {
        stubEmbeddingOk();
        stubSearch(List.of(hit("c1", "a1", "0.8200")));

        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("账号登录失败怎么办", null, null);

        Assertions.assertEquals(OfficeDomain.OFFICE_IT, outcome.domain(),
                "普通登录排障不能因含「账号」被误拦（AI-001）");
        Assertions.assertNull(outcome.suggestedRefusalReason());
    }

    /**
     * 寒暄类输入判 UNCERTAIN，同样零检索调用，交由上层反问澄清引导用户补充问题。
     */
    @Test
    public void vagueQuestionIsUncertainAndSkipsRetrieval() {
        RagRetrievalService.RetrievalOutcome outcome = service.retrieve("你好", null, null);

        Assertions.assertEquals(OfficeDomain.UNCERTAIN, outcome.domain());
        verifyNoInteractions(embeddingService, indexService);
    }

    // ------------------------------------------------------------ 引用校验

    /**
     * AI-008 引用校验：
     *   - 同一文章多个切片命中只取最高分一条（a1 的 0.90 胜出，0.70 丢弃）；
     *   - 非 PUBLISHED 状态（a2 已 OFFLINE）整体剔除，下线知识绝不出现在引用里。
     */
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

    /**
     * 引用摘要按配置的 snippetLength 截断（防超长正文撑爆消息体），
     * 标题缺失时退化为正文片段充当标题，保证前端永远有内容可展示。
     */
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

    /**
     * 对外响应契约：RetrievalOutcome -> RagRetrievalResponse 的完整映射 ——
     * items/domain/replyType/publishedOnly/reliable 齐全，供 consultation-service 消费。
     */
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

    /**
     * 参数钳制：调用方传入 topK=999 这类越界值时，实际检索必须改用配置的 maxTopK，
     * 防止恶意/笔误参数把 ES 打垮。
     */
    @Test
    public void topKIsClampedToConfiguredMaximum() {
        stubEmbeddingOk();
        Mockito.when(indexService.searchTopKChunks(anyList(), anyString(), any(), anyInt())).thenReturn(List.of());

        service.retrieve("VPN 连不上怎么办", "C_NET", 999);

        Mockito.verify(indexService).searchTopKChunks(anyList(), anyString(), eq("C_NET"),
                eq(properties.getMaxTopK()));
    }

    /**
     * 空白提问在入口处直接 BizException 拒绝，不进入判定与检索管线。
     */
    @Test
    public void blankQuestionIsRejected() {
        Assertions.assertThrows(BizException.class, () -> service.retrieve("   ", null, null));
    }

    /**
     * 本地断言辅助，避免过度暴露 RetrievedChunk 的字段细节：
     * 一次性核对一个检索结果项的全部身份字段（chunk/article/version/indexVersion），
     * 防止未来给 record 增删字段时所有用例都要逐条改断言。
     */
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
