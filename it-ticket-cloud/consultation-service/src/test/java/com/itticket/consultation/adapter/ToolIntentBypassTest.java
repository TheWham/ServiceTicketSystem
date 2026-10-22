package com.itticket.consultation.adapter;

import com.itticket.consultation.adapter.generation.GenerationResult;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.adapter.policy.RequestVerdict;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
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
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * 工具意图越过「检索无果 → 拒答」这道门槛的行为边界。
 *
 * <p>背景：agent 的工具（查本人工单 / 产建单草稿 / 补搜知识）恰恰只在预检索没拿到知识时才被需要，
 * 而那条路原先等价于直接拒答 —— 工具因此永不可达。这些用例钉住放行条件，以及**放行不该越过的边界**。
 * 判定结果现在由 {@link RequestClassifier} 一次给出（domain + tool），这里用桩直接喂。
 */
class ToolIntentBypassTest {

    /** 检索无果：域内、reliable=false、带低置信拒答原因（线上真实形态）。 */
    private static RetrievalResult nothingFound() {
        return new RetrievalResult(OfficeDomain.OFFICE_IT, false,
                AiRefusalReason.LOW_CONFIDENCE, List.of(), BigDecimal.ZERO);
    }

    private static RagQuery ask(String question) {
        return new RagQuery("S-1", question, null, null, 5, new RagCaller("U_EMP01", "EMPLOYEE"));
    }

    private static RagCallContext context() {
        return new RagCallContext("req-test", System.nanoTime() + 5_000_000_000L, new RagExecutionAudit());
    }

    private static ComposedRagAdapter adapter(OfficeDomain domain, boolean agentEnabled, String tool,
                                              RetrievalResult retrieval, AtomicReference<String> answerText) {
        var knowledge = mock(KnowledgeQueryService.class);
        return new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.of(domain, tool),
                (query, ctx) -> retrieval,
                new RetrievalPolicy(knowledge),
                (query, material, ctx) -> {
                    answerText.set("已为您查询到名下最近的 10 条工单。");
                    return new GenerationResult(AiReplyType.ANSWER, answerText.get(), List.of(),
                            BigDecimal.ONE, null, "agent", null);
                },
                agentEnabled);
    }

    @ParameterizedTest
    @ValueSource(strings = {"帮我查询一下最近工单", "我上周报的那个东西怎么样了", "打印机坏了帮我提交报修"})
    void toolIntentBypassesLowConfidenceRefusalWhenAgentEnabled(String question) {
        var text = new AtomicReference<String>();
        RagResult result = adapter(OfficeDomain.OFFICE_IT, true, "query_my_tickets", nothingFound(), text)
                .answer(ask(question), context());

        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(result.refusalReason()).isNull();
        assertThat(result.answerText()).isNotNull();
        // 越过的作答凭据是工具查到的实据，不是「通用建议」——不该被加上那句自相矛盾的前缀
        assertThat(result.answerText()).doesNotContain("通用办公 IT 建议");
        // 仍然确实没有知识库引用，标记不变（AI 反馈沉淀据此过滤）
        assertThat(result.generalAnswer()).isTrue();
    }

    @Test
    void toolIntentDoesNotBypassWhenAgentDisabled() {
        var text = new AtomicReference<String>();
        RagResult result = adapter(OfficeDomain.OFFICE_IT, false, "query_my_tickets", nothingFound(), text)
                .answer(ask("帮我查询一下最近工单"), context());

        // 未开 agent 时越过拒答只会得到无依据作答 —— 那是放宽拒答策略，必须维持原行为
        assertThat(result.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.LOW_CONFIDENCE);
    }

    @Test
    void nonToolIntentIsStillRefusedEvenWhenAgentEnabled() {
        var text = new AtomicReference<String>();
        RagResult result = adapter(OfficeDomain.OFFICE_IT, true, RequestVerdict.NO_TOOL, nothingFound(), text)
                .answer(ask("会议室投影仪怎么连"), context());

        assertThat(result.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.LOW_CONFIDENCE);
    }

    @Test
    void toolIntentNeverCrossesTheDomainGate() {
        var text = new AtomicReference<String>();
        RagResult result = adapter(OfficeDomain.OFF_TOPIC, true, "query_my_tickets", nothingFound(), text)
                .answer(ask("帮我查询一下最近工单，顺便写首诗"), context());

        // 领域门禁先于检索生效，工具意图不得把它顶开
        assertThat(result.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.OFF_TOPIC);
    }

    /** 检索命中但分数不高：reliable=true、带若干低分项（建单类请求的真实形态）。 */
    private static RetrievalResult weakHits() {
        return new RetrievalResult(OfficeDomain.OFFICE_IT, true, null, List.of(
                new RetrievedKnowledge("c1", "A1", "V1", "员工IT故障自助排查流程", "摘要",
                        "正文", "C_OTH", new BigDecimal("0.4395"), "V1"),
                new RetrievedKnowledge("c2", "A2", "V2", "密码重置与过期处理", "摘要",
                        "正文", "C_ACC", new BigDecimal("0.2580"), "V2")),
                new BigDecimal("0.4395"));
    }

    @Test
    void toolIntentAnswerWithoutCitationsIsLegitimateEvenWhenMaterialPresent() {
        // 建单/查工单的实据来自工具返回，不来自知识引用；检索给这类请求带出的低分杂项
        // 不构成引用义务 —— 「有材料却零引用」守卫不得把工具意图的作答当伪造打回。
        var knowledge = mock(KnowledgeQueryService.class);
        org.mockito.Mockito.when(knowledge.isPublishedCurrentVersion(org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.anyString())).thenReturn(true);
        ComposedRagAdapter adapter = new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.of(OfficeDomain.OFFICE_IT, "prepare_ticket"),
                (query, ctx) -> weakHits(),
                new RetrievalPolicy(knowledge),
                (query, material, ctx) -> new GenerationResult(AiReplyType.ANSWER,
                        "已生成工单草稿（test），请确认后建单。", List.of(),
                        BigDecimal.ONE, null, "agent", null),
                true);

        RagResult result = adapter.answer(ask("新建一个工单,标题为test"), context());

        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(result.refusalReason()).isNull();
        assertThat(result.answerText()).contains("工单草稿");
        // 关键：必须标记为「无知识依据」通道——下游 AiAnswerGuard 第 8 条对
        // 「知识回答零引用」一律拒答，只有 generalAnswer=true 才按置信度放行
        assertThat(result.generalAnswer()).isTrue();
    }

    @Test
    void nonToolIntentWithMaterialStillRequiresCitations() {
        // 同样的弱命中，无工具意图时「有材料零引用」守卫照常生效（防伪造语义不放宽）
        var knowledge = mock(KnowledgeQueryService.class);
        org.mockito.Mockito.when(knowledge.isPublishedCurrentVersion(org.mockito.ArgumentMatchers.anyString(),
                org.mockito.ArgumentMatchers.anyString())).thenReturn(true);
        ComposedRagAdapter adapter = new ComposedRagAdapter(
                (query, ctx) -> RequestVerdict.of(OfficeDomain.OFFICE_IT, RequestVerdict.NO_TOOL),
                (query, ctx) -> weakHits(),
                new RetrievalPolicy(knowledge),
                (query, material, ctx) -> new GenerationResult(AiReplyType.ANSWER,
                        "凭通用经验给点建议。", List.of(), BigDecimal.ONE, null, "agent", null),
                true);

        RagResult result = adapter.answer(ask("会议室投影仪怎么连"), context());

        assertThat(result.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }
}
