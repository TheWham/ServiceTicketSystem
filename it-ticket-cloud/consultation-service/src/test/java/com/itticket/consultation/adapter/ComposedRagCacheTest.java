package com.itticket.consultation.adapter;

import com.itticket.consultation.adapter.cache.SemanticAnswerCache;
import com.itticket.consultation.adapter.generation.GenerationResult;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.adapter.policy.RequestVerdict;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
import com.itticket.consultation.adapter.retrieval.RetrievalPolicy;
import com.itticket.consultation.adapter.retrieval.RetrievalResult;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.TicketDraftDto;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.service.KnowledgeQueryService;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Clock;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * ComposedRagAdapter 语义缓存接线的行为边界：安全裁决先于缓存、工具旁路双跳过、
 * 门控写入（只收带引用的实证答案）、命中产出与真实延迟。
 *
 * <p>关键先序断言：域门禁（restrict）先于 cache.lookup——预先手工植入同题缓存条目后，
 * HIGH_RISK 判定必须仍然拒答且不产生 hits。
 */
class ComposedRagCacheTest {

    private static final String QUESTION = "会议没有声音怎么处理";

    private static RagQuery ask(String question) {
        return new RagQuery("S-1", question, null, null, 5, new RagCaller("U_EMP01", "EMPLOYEE"));
    }

    private static RagCallContext context() {
        return new RagCallContext("req-cache-test", System.nanoTime() + 5_000_000_000L,
                new RagExecutionAudit());
    }

    /** 带一条可靠材料的检索结果（policy.material 会放行）。 */
    private static RetrievalResult reliable() {
        return new RetrievalResult(OfficeDomain.OFFICE_IT, true, null, List.of(
                new RetrievedKnowledge("c1", "A1", "V1", "会议音频排障", "摘要",
                        "正文内容", "C_NET", new BigDecimal("0.85"), "V1", null, null, null)),
                new BigDecimal("0.85"));
    }

    /** 检索无果：域内、reliable=false、低置信拒答原因。 */
    private static RetrievalResult nothingFound() {
        return new RetrievalResult(OfficeDomain.OFFICE_IT, false,
                AiRefusalReason.LOW_CONFIDENCE, List.of(), BigDecimal.ZERO);
    }

    /** 开启语义缓存 + 固定向量(同一问题两次调用嵌入结果一致)。 */
    private static SemanticAnswerCache enabledCache() {
        ConsultationProperties.Ai.Cache config = new ConsultationProperties.Ai.Cache();
        config.setEnabled(true);
        config.setEmbeddingModel("test-embed");
        return enabledCache(config, (text, ctx) -> new float[]{1f, 0f});
    }

    private static SemanticAnswerCache enabledCache(ConsultationProperties.Ai.Cache config,
                                                    com.itticket.consultation.adapter.embedding.EmbeddingClient embeddings) {
        return new SemanticAnswerCache(config, embeddings, (article, version) -> true, Clock.systemUTC());
    }

    private static RetrievalPolicy policy() {
        KnowledgeQueryService knowledge = mock(KnowledgeQueryService.class);
        when(knowledge.isPublishedCurrentVersion(org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.anyString())).thenReturn(true);
        return new RetrievalPolicy(knowledge, Set.of("SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES"),
                new BigDecimal("0.10"), 2);
    }

    /** 默认编排桩：域内、无工具、正常知识作答(单条引用)。 */
    private static ComposedRagAdapter adapter(OfficeDomain domain, String tool,
                                              RetrievalResult retrieval, SemanticAnswerCache cache,
                                              GenerationResult generation, AtomicInteger retrievals,
                                              AtomicInteger generations) {
        return new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.of(domain, tool),
                (query, ctx) -> { retrievals.incrementAndGet(); return retrieval; },
                policy(),
                (query, material, ctx, sink) -> { generations.incrementAndGet(); return generation; },
                false, null,
                cache);
    }

    private static GenerationResult knowledgeAnswer() {
        return new GenerationResult(AiReplyType.ANSWER, "请检查麦克风与会议客户端的音频输入设置。",
                List.of("V1"), new BigDecimal("0.91"), null, "m", null);
    }

    @Test
    void disabledCacheKeepsCurrentBehaviorAndNeverWrites() {
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        SemanticAnswerCache cache = SemanticAnswerCache.disabled();
        RagResult result = adapter(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations)
                .answer(ask(QUESTION), context(), TokenSink.discarding());

        assertThat(result.status()).isEqualTo(RagStatus.SUCCESS);
        assertThat(result.cacheHit()).isNull();
        assertThat(retrievals.get()).isEqualTo(1);
        assertThat(generations.get()).isEqualTo(1);
        assertThat(cache.stats().entries()).isZero();
    }

    @Test
    void firstMissThenHitSkipsRetrievalAndGeneration() {
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        SemanticAnswerCache cache = enabledCache();
        ComposedRagAdapter rag = adapter(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations);

        RagResult first = rag.answer(ask(QUESTION), context(), TokenSink.discarding());
        assertThat(first.cacheHit()).isNull();
        assertThat(first.citations()).hasSize(1);
        assertThat(cache.stats().entries()).isEqualTo(1);

        RagResult hit = rag.answer(ask(QUESTION), context(), TokenSink.discarding());
        assertThat(hit.cacheHit()).isNotNull();
        assertThat(hit.cacheHit().similarity()).isEqualTo(1.0);
        assertThat(hit.answerText()).isEqualTo(first.answerText());
        assertThat(hit.citations()).containsExactlyElementsOf(first.citations());
        assertThat(hit.latencyMs()).isGreaterThanOrEqualTo(0);
        // 命中后实时链路完全未被触达
        assertThat(retrievals.get()).isEqualTo(1);
        assertThat(generations.get()).isEqualTo(1);
        assertThat(cache.stats().hits()).isEqualTo(1);
    }

    @Test
    void domainRefusalIsCheckedBeforeCacheLookup() {
        // 手工植入「同题」缓存条目:即便问法完全一致, HIGH_RISK 判定也必须先拒答
        SemanticAnswerCache cache = enabledCache();
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        ComposedRagAdapter honest = adapter(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations);
        honest.answer(ask(QUESTION), context(), TokenSink.discarding());
        assertThat(cache.stats().entries()).isEqualTo(1);

        RagResult refused = adapter(OfficeDomain.HIGH_RISK, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations)
                .answer(ask(QUESTION), context(), TokenSink.discarding());

        assertThat(refused.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(refused.refusalReason()).isEqualTo(AiRefusalReason.HIGH_RISK_TOPIC);
        // 门禁先于缓存:hits 必须为 0, 拒答也不得覆盖诚实的缓存条目
        assertThat(cache.stats().hits()).isZero();
        assertThat(cache.stats().entries()).isEqualTo(1);
        assertThat(retrievals.get()).isEqualTo(1);
    }

    @Test
    void toolBypassSkipsBothLookupAndWrite() {
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        SemanticAnswerCache cache = enabledCache();
        GenerationResult toolAnswer = new GenerationResult(AiReplyType.ANSWER,
                "已为您查询到名下最近的 10 条工单。", List.of(), BigDecimal.ONE, null, "agent", null);
        ComposedRagAdapter rag = new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.of(OfficeDomain.OFFICE_IT, "query_my_tickets"),
                (query, ctx) -> { retrievals.incrementAndGet(); return nothingFound(); },
                policy(),
                (query, material, ctx, sink) -> { generations.incrementAndGet(); return toolAnswer; },
                true, null,
                cache);

        RagResult result = rag.answer(ask("帮我查询最近工单"), context(), TokenSink.discarding());

        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(result.cacheHit()).isNull();
        // 工具实据是用户私有事实,不读也不写公共缓存池
        assertThat(cache.stats().entries()).isZero();
        assertThat(cache.stats().hits()).isZero();
        assertThat(cache.stats().realMisses()).isZero();
    }

    @Test
    void embeddingFailureFallsThroughToRealtimePathWithoutDegrading() {
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        ConsultationProperties.Ai.Cache config = new ConsultationProperties.Ai.Cache();
        config.setEnabled(true);
        config.setEmbeddingModel("test-embed");
        SemanticAnswerCache cache = enabledCache(config, (text, ctx) -> {
            throw DependencyFailure.invalid();
        });
        ComposedRagAdapter rag = adapter(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations);

        RagResult result = rag.answer(ask(QUESTION), context(), TokenSink.discarding());

        // 缓存嵌入挂了不能拖垮实时链路; lookup+write 两次嵌入尝试都按依赖失败计数
        assertThat(result.status()).isEqualTo(RagStatus.SUCCESS);
        assertThat(result.refusalReason()).isNull();
        assertThat(result.cacheHit()).isNull();
        assertThat(retrievals.get()).isEqualTo(1);
        assertThat(generations.get()).isEqualTo(1);
        assertThat(cache.stats().depFailures()).isEqualTo(2);
        assertThat(cache.stats().entries()).isZero();
    }

    @Test
    void clarifyAndDependencyFailuresAreNeverWritten() {
        // UNCERTAIN → 罐头 CLARIFY: 在检索/生成之前就返回, 更不该触碰缓存
        SemanticAnswerCache cache = enabledCache();
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        RagResult clarify = adapter(OfficeDomain.UNCERTAIN, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations)
                .answer(ask(QUESTION), context(), TokenSink.discarding());
        assertThat(clarify.replyType()).isEqualTo(AiReplyType.CLARIFY);
        assertThat(cache.stats().entries()).isZero();

        // 依赖故障被编排器折叠为 failure 结果: 同样不写
        RagResult failed = new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.of(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL),
                (query, ctx) -> { throw DependencyFailure.invalid(); },
                policy(),
                (query, material, ctx, sink) -> knowledgeAnswer(),
                false, null,
                cache)
                .answer(ask(QUESTION), context(), TokenSink.discarding());
        assertThat(failed.status()).isNotEqualTo(RagStatus.SUCCESS);
        assertThat(cache.stats().entries()).isZero();
    }

    @Test
    void cacheHitStreamsWholeAnswerAsASingleToken() {
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        SemanticAnswerCache cache = enabledCache();
        ComposedRagAdapter rag = adapter(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations);

        // 未命中:令牌由真实生成器外发(本测试生成桩不外发),适配器自身不得额外发字
        List<String> firstTokens = new CopyOnWriteArrayList<>();
        rag.answer(ask(QUESTION), context(), TokenSink.of(firstTokens::add));
        assertThat(firstTokens).isEmpty();

        // 命中:适配器把缓存答案整段单发一次,服务层无需感知"这条来自缓存"
        List<String> hitTokens = new CopyOnWriteArrayList<>();
        RagResult hit = rag.answer(ask(QUESTION), context(), TokenSink.of(hitTokens::add));
        assertThat(hit.cacheHit()).isNotNull();
        assertThat(hitTokens).containsExactly(hit.answerText());
    }

    @Test
    void refusalAndClarifyNeverEmitTokens() {
        SemanticAnswerCache cache = enabledCache();
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();

        List<String> refusedTokens = new CopyOnWriteArrayList<>();
        RagResult refused = adapter(OfficeDomain.HIGH_RISK, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations)
                .answer(ask(QUESTION), context(), TokenSink.of(refusedTokens::add));
        assertThat(refused.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(refusedTokens).isEmpty();

        List<String> clarifyTokens = new CopyOnWriteArrayList<>();
        RagResult clarified = adapter(OfficeDomain.UNCERTAIN, RequestVerdict.NO_TOOL, reliable(),
                cache, knowledgeAnswer(), retrievals, generations)
                .answer(ask(QUESTION), context(), TokenSink.of(clarifyTokens::add));
        assertThat(clarified.replyType()).isEqualTo(AiReplyType.CLARIFY);
        assertThat(clarifyTokens).isEmpty();
    }

    @Test
    void ticketDraftResultsAreNeverCached() {
        AtomicInteger retrievals = new AtomicInteger();
        AtomicInteger generations = new AtomicInteger();
        SemanticAnswerCache cache = enabledCache();
        // Python 代理 ReAct 可在 Java 判定 NO_TOOL 时带外产出草稿:草稿承载提问者的具体环境
        // (标题/分类/描述/资产),跨用户重放等于泄露;即使同用户,冻结草稿也劣于实时重答。
        GenerationResult draftAnswer = new GenerationResult(AiReplyType.ANSWER,
                "已生成工单草稿,请确认。", List.of("V1"), new BigDecimal("0.91"), null, "m",
                new TicketDraftDto("打印机故障", "C_HW_PRT", "打印机无法进纸", "MEDIUM"));
        ComposedRagAdapter rag = adapter(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL, reliable(),
                cache, draftAnswer, retrievals, generations);

        RagResult first = rag.answer(ask("新建打印机报修工单"), context(), TokenSink.discarding());
        assertThat(first.ticketDraft()).isNotNull();
        assertThat(cache.stats().entries()).isZero();

        RagResult second = rag.answer(ask("新建打印机报修工单"), context(), TokenSink.discarding());
        assertThat(second.cacheHit()).isNull();
        assertThat(second.ticketDraft()).isEqualTo(first.ticketDraft());
        assertThat(second.answerText()).isEqualTo(first.answerText());
        assertThat(retrievals.get()).isEqualTo(2);
    }
}
