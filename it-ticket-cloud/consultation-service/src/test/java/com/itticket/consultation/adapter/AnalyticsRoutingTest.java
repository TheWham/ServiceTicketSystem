package com.itticket.consultation.adapter;

import com.itticket.consultation.adapter.policy.KeywordRequestClassifier;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.adapter.policy.RequestVerdict;
import com.itticket.consultation.adapter.retrieval.RetrievalPolicy;
import com.itticket.consultation.adapter.retrieval.RetrievalResult;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.service.KnowledgeQueryService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.math.BigDecimal;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * 跨工单分析请求的路由边界。
 *
 * <p>这条链路的失败模式与普通问答不同：判成分析型却答不了，用户会收到一份"答非所问"的
 * 统计报告；而判错了还要**跨服务边界**回退给 RAG，代价比同一进程内选错分支高。所以：
 * ① 分析判定必须落在 OFFICE_IT 域内（越界请求没有"做统计"的余地）；
 * ② 分析链路不可用时如实拒答，不得回退成知识问答。
 */
class AnalyticsRoutingTest {

    private static RagQuery ask(String question) {
        return new RagQuery("S-1", question, null, null, 5, new RagCaller("U_ENG01", "ENGINEER"));
    }

    private static RagCallContext context() {
        return new RagCallContext("req-test", System.nanoTime() + 5_000_000_000L,
                new RagExecutionAudit());
    }

    private static RetrievalResult anything() {
        return new RetrievalResult(OfficeDomain.OFFICE_IT, true, null, List.of(), BigDecimal.ONE);
    }

    // ---------------------------------------------------------------- 路由

    @Test
    void 分析判定不落进检索() {
        // 分析要的是工单集的分布，不是知识卡片；先检索一遍纯属浪费，且会把
        // "统计请求"引向单卡答案 —— 那正是这条链路要消灭的答非所问。
        AtomicBoolean retrieved = new AtomicBoolean(false);
        var adapter = new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.analyticsRequest(),
                (query, ctx) -> { retrieved.set(true); return anything(); },
                new RetrievalPolicy(mock(KnowledgeQueryService.class), java.util.Set.of(), new BigDecimal("0.10"), 2),
                (query, material, ctx, sink) -> {
                    throw new AssertionError("分析路径不应调用知识生成器");
                },
                false, null, com.itticket.consultation.adapter.cache.SemanticAnswerCache.disabled());

        RagResult result = adapter.answer(ask("总结本季度各类故障的分布"), context(), com.itticket.consultation.adapter.TokenSink.discarding());

        assertThat(retrieved).isFalse();
        assertThat(result.replyType()).isEqualTo(AiReplyType.REFUSE);
    }

    @Test
    void 分析链路未启用时如实拒答而不回退知识问答() {
        // 回退会让统计请求收到单卡答案；如实拒答至少让人知道"这个能力没开"。
        var adapter = new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.analyticsRequest(),
                (query, ctx) -> anything(),
                new RetrievalPolicy(mock(KnowledgeQueryService.class), java.util.Set.of(), new BigDecimal("0.10"), 2),
                (query, material, ctx, sink) -> new com.itticket.consultation.adapter.generation.GenerationResult(
                        AiReplyType.ANSWER, "知识库里的排查步骤……", List.of(), BigDecimal.ONE,
                        null, "test", null),
                false, null, com.itticket.consultation.adapter.cache.SemanticAnswerCache.disabled());

        RagResult result = adapter.answer(ask("统计本季度全部工单的故障分布"), context(), com.itticket.consultation.adapter.TokenSink.discarding());

        assertThat(result.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.MODEL_UNAVAILABLE);
    }

    @Test
    void 越界域带分析标记时门禁优先() {
        // RequestVerdict 的不变量：非 OFFICE_IT 一律把 analytics 压回 false，
        // 越界请求不可能借"做统计"的名义越过领域门禁。
        RequestVerdict verdict = new RequestVerdict(OfficeDomain.OFF_TOPIC,
                RequestVerdict.NO_TOOL, true);

        assertThat(verdict.analytics()).isFalse();
    }

    @Test
    void 高风险域带分析标记时同样被压回() {
        RequestVerdict verdict = new RequestVerdict(OfficeDomain.HIGH_RISK,
                RequestVerdict.NO_TOOL, true);

        assertThat(verdict.analytics()).isFalse();
    }

    @Test
    void 分析请求不携带工具() {
        // 分析不是 function call；带上工具名会让下游误走工具意图旁路。
        assertThat(RequestVerdict.analyticsRequest().tool()).isEqualTo(RequestVerdict.NO_TOOL);
        assertThat(RequestVerdict.analyticsRequest().domain()).isEqualTo(OfficeDomain.OFFICE_IT);
    }

    // ---------------------------------------------------------------- 关键词兜底判定

    @ParameterizedTest
    @ValueSource(strings = {
            "请根据全部网络与打印设备工单，总结本季度共性根因",
            "统计一下各类故障的占比",
            "本季度工单的故障分布情况",
            "给出下季度的备件采购建议",
            "分析近 90 天的故障趋势",
            "盘点今年所有工单的规律",
    })
    void 关键词兜底识别分析型请求(String question) {
        RequestVerdict verdict = new KeywordRequestClassifier().classify(ask(question), context());

        assertThat(verdict.analytics()).isTrue();
        assertThat(verdict.domain()).isEqualTo(OfficeDomain.OFFICE_IT);
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "我的 VPN 连不上怎么办",
            "电脑蓝屏怎么排查",
            "打印机脱机了怎么处理",
            "帮我总结一下这个报错",
            "帮我建一张工单",
    })
    void 关键词兜底不把普通问题判成分析型(String question) {
        RequestVerdict verdict = new KeywordRequestClassifier().classify(ask(question), context());

        assertThat(verdict.analytics()).isFalse();
    }
}