package com.itticket.consultation.service;

import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;
import java.util.function.BiPredicate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * AI 输出守卫(AI-001 能力边界 / AI-008 上线前校验)纯单元测试,对应 AC-01、AC-02。
 *
 * <p>契约来源:
 * <ul>
 *   <li>AI-001:合法 IT 问题允许通用回答；知识冲突、风险或依赖不可用仍拒答。
 *       有效回答不因置信度低而拒答；分数保留用于审计及转人工建议。</li>
 *   <li>AI-003 / AI-004.3:拒答必须给结构化 refusalReason,REFUSE 时 answerText 为空;</li>
 *   <li>AI-008:引用必须指向仍为 PUBLISHED 的当前版本,失效即整体拒答(AC-27 知识下线场景);</li>
 *   <li>RD-006:RAG/模型不可用时返回拒答并保留转人工与直接提单入口,不得生成无来源猜测答案;</li>
 *   <li>AC-01 基于知识回答成功并展示来源；无可靠知识时允许空引用通用回答并保留转人工入口。</li>
 * </ul>
 */
class AiAnswerGuardTest {

    @Test
    void semanticHighRiskDecisionCannotBeOverriddenByGeneratedAnswer() {
        RagResult result = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "执行操作", List.of(),
                BigDecimal.ONE, false, "model", List.of(), 10, null, true, false, true);
        assertRefusal(evaluate(result), AiRefusalReason.HIGH_RISK_TOPIC);
    }

    @Test
    void offTopicFlagCannotBeOverriddenByAnswerReplyType() {
        RagResult result = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "越界内容", List.of(),
                BigDecimal.ONE, false, "model", List.of(), 10, null, true, true);
        assertRefusal(evaluate(result), AiRefusalReason.OFF_TOPIC);
    }

    @Test
    void clarificationDoesNotNeedKnowledgeCitation() {
        RagResult result = new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY, "请补充设备和现象", List.of(),
                BigDecimal.ONE, false, "model", List.of(), 10, null);
        assertThat(evaluate(result).replyType()).isEqualTo(AiReplyType.CLARIFY);
    }

    @Test
    void generalAnswerCannotHideInvalidCitations() {
        RagResult result = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "通用答案", CITATIONS,
                BigDecimal.ONE, false, "model", List.of(), 10, null, true, false);
        assertRefusal(evaluate(result), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    private static final List<KnowledgeCitationDto> CITATIONS = List.of(
            new KnowledgeCitationDto("KA-0001", "KV-0001", "VPN 接入指引",
                    new BigDecimal("0.9100"), "打开客户端并使用域账号登录。"));

    private static final String ANSWER_TEXT = "请打开 VPN 客户端并使用域账号登录。";

    /** 默认:所有引用仍是 PUBLISHED 的当前版本。 */
    private static final BiPredicate<String, String> ALL_PUBLISHED = (articleId, versionId) -> true;

    /** 模拟知识已下线:任何引用都不再是当前发布版本(AI-008 / AC-27)。 */
    private static final BiPredicate<String, String> NONE_PUBLISHED = (articleId, versionId) -> false;

    private static ConsultationProperties.Ai properties() {
        ConsultationProperties.Ai ai = new ConsultationProperties.Ai();
        ai.setAnswerEnabled(true);
        ai.setMinConfidence(new BigDecimal("0.60"));
        ai.setSuggestTransferBelowConfidence(new BigDecimal("0.75"));
        return ai;
    }

    /** 一个「完美」的模型成功结果:SUCCESS + ANSWER + 有效引用 + 高置信度。 */
    private static RagResult perfect(String confidence) {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, ANSWER_TEXT, CITATIONS,
                new BigDecimal(confidence), false, "local-rag-1.0", List.of("KV-0001"), 120L, null);
    }

    private static RagResult withCitations(List<KnowledgeCitationDto> citations) {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, ANSWER_TEXT, citations,
                new BigDecimal("0.90"), false, "local-rag-1.0", List.of("KV-0001"), 120L, null);
    }

    private static AiAnswerGuard.Verdict evaluate(RagResult result) {
        return AiAnswerGuard.evaluate(result, properties(), false, ALL_PUBLISHED);
    }

    /** AI-004.3 + AI-001:所有拒答形态的公共不变式。 */
    private static void assertRefusal(AiAnswerGuard.Verdict verdict, AiRefusalReason expected) {
        assertThat(verdict.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(verdict.refusalReason()).isEqualTo(expected);
        assertThat(verdict.answerText()).isNull();
        assertThat(verdict.citations()).isEmpty();
        // 拒答必须始终给出转人工入口(AI-001、RD-006)
        assertThat(verdict.suggestTransfer()).isTrue();
        assertThat(verdict.confidence()).isNotNull();
    }

    // ------------------------------------------------------------------
    // 一、成功路径(AC-01)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-01 基于知识回答成功:ANSWER + 非空引用 + 无拒答原因")
    void ac01_answer_with_valid_citation_passes_the_guard() {
        AiAnswerGuard.Verdict verdict = evaluate(perfect("0.90"));

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.answerText()).isEqualTo(ANSWER_TEXT);
        assertThat(verdict.citations()).isEqualTo(CITATIONS).isNotEmpty();
        assertThat(verdict.refusalReason()).isNull();
        assertThat(verdict.confidence()).isEqualByComparingTo(new BigDecimal("0.90"));
        // 置信度高于建议转人工阈值时不主动引导转人工
        assertThat(verdict.suggestTransfer()).isFalse();
    }

    @Test
    @DisplayName("旧 minConfidence(0.60)边界不影响回答放行")
    void ac01_confidence_exactly_at_min_threshold_is_allowed() {
        AiAnswerGuard.Verdict verdict = evaluate(perfect("0.60"));

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.refusalReason()).isNull();
        assertThat(verdict.confidence()).isEqualByComparingTo(new BigDecimal("0.60"));
    }

    @Test
    @DisplayName("AC-01 CLARIFY(澄清提问)保留既有协议处理")
    void ac01_clarify_reply_type_is_preserved() {
        RagResult clarify = new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY,
                "请问是内网还是外网无法访问?", CITATIONS, new BigDecimal("0.80"),
                false, "local-rag-1.0", List.of("KV-0001"), 90L, null);

        AiAnswerGuard.Verdict verdict = evaluate(clarify);

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.CLARIFY);
        assertThat(verdict.refusalReason()).isNull();
    }

    @Test
    @DisplayName("AC-01 replyType 缺省时按 ANSWER 处理(AI-003 默认值)")
    void ac01_null_reply_type_defaults_to_answer() {
        RagResult noType = new RagResult(RagStatus.SUCCESS, null, ANSWER_TEXT, CITATIONS,
                new BigDecimal("0.88"), false, "local-rag-1.0", List.of("KV-0001"), 90L, null);

        AiAnswerGuard.Verdict verdict = evaluate(noType);

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.refusalReason()).isNull();
    }

    // ------------------------------------------------------------------
    // 二、判定优先级(先命中先返回,RD-013 降级原因唯一可判定)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-02 answerEnabled=false 时即便是完美回答也返回 POLICY_BLOCKED(PRD 17.3 / RD-006)")
    void ac02_policy_blocked_wins_over_a_perfect_answer() {
        ConsultationProperties.Ai disabled = properties();
        disabled.setAnswerEnabled(false);

        AiAnswerGuard.Verdict verdict =
                AiAnswerGuard.evaluate(perfect("0.99"), disabled, false, ALL_PUBLISHED);

        assertRefusal(verdict, AiRefusalReason.POLICY_BLOCKED);
        assertThat(verdict.confidence()).isEqualByComparingTo(RagResult.ZERO_CONFIDENCE);
    }

    @Test
    @DisplayName("AC-02 高风险主题优先于一切模型结果:HIGH_RISK_TOPIC(AI-001)")
    void ac02_high_risk_topic_wins_over_model_result() {
        AiAnswerGuard.Verdict verdict =
                AiAnswerGuard.evaluate(perfect("0.99"), properties(), true, ALL_PUBLISHED);

        assertRefusal(verdict, AiRefusalReason.HIGH_RISK_TOPIC);
        assertThat(verdict.confidence()).isEqualByComparingTo(RagResult.ZERO_CONFIDENCE);
    }

    @Test
    @DisplayName("AC-02 高风险命中时即便依赖超时也返回 HIGH_RISK_TOPIC,拒答原因唯一")
    void ac02_high_risk_topic_wins_over_dependency_failure() {
        RagResult timeout = RagResult.degraded(RagStatus.TIMEOUT, "TIMEOUT", 15000L);

        AiAnswerGuard.Verdict verdict =
                AiAnswerGuard.evaluate(timeout, properties(), true, ALL_PUBLISHED);

        assertRefusal(verdict, AiRefusalReason.HIGH_RISK_TOPIC);
    }

    @Test
    @DisplayName("AC-02 answerEnabled=false 优先于高风险命中:POLICY_BLOCKED 是第一道闸门")
    void ac02_policy_blocked_wins_over_high_risk_topic() {
        ConsultationProperties.Ai disabled = properties();
        disabled.setAnswerEnabled(false);

        AiAnswerGuard.Verdict verdict =
                AiAnswerGuard.evaluate(perfect("0.99"), disabled, true, ALL_PUBLISHED);

        assertRefusal(verdict, AiRefusalReason.POLICY_BLOCKED);
    }

    // ------------------------------------------------------------------
    // 三、依赖故障与 Schema 违规(RD-006 / AI-004)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-02 RAG 超时:MODEL_UNAVAILABLE,保留转人工入口(RD-006)")
    void ac02_timeout_maps_to_model_unavailable() {
        assertRefusal(evaluate(RagResult.degraded(RagStatus.TIMEOUT, "TIMEOUT", 15000L)),
                AiRefusalReason.MODEL_UNAVAILABLE);
    }

    @Test
    @DisplayName("AC-02 RAG 不可用/断路器打开:MODEL_UNAVAILABLE(RD-006 / RD-007)")
    void ac02_unavailable_maps_to_model_unavailable() {
        assertRefusal(evaluate(RagResult.degraded(RagStatus.UNAVAILABLE, "CIRCUIT_OPEN", 1L)),
                AiRefusalReason.MODEL_UNAVAILABLE);
    }

    @Test
    @DisplayName("AC-02 适配器返回 null 或 status 缺失:MODEL_UNAVAILABLE,不得当作成功")
    void ac02_null_result_maps_to_model_unavailable() {
        assertRefusal(evaluate(null), AiRefusalReason.MODEL_UNAVAILABLE);

        RagResult noStatus = new RagResult(null, AiReplyType.ANSWER, ANSWER_TEXT, CITATIONS,
                new BigDecimal("0.90"), false, "local-rag-1.0", List.of("KV-0001"), 10L, null);
        assertRefusal(evaluate(noStatus), AiRefusalReason.MODEL_UNAVAILABLE);
    }

    @Test
    @DisplayName("AC-02 模型输出不合 AI-004 Schema:NO_RELIABLE_KNOWLEDGE,不得用常识补写")
    void ac02_invalid_response_maps_to_no_reliable_knowledge() {
        assertRefusal(evaluate(RagResult.degraded(RagStatus.INVALID_RESPONSE, "INVALID_RESPONSE", 80L)),
                AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    // ------------------------------------------------------------------
    // 四、业务性拒答(AI-001)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-02 topK 内知识冲突:CONFLICTING_KNOWLEDGE")
    void ac02_knowledge_conflict_maps_to_conflicting_knowledge() {
        RagResult conflict = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, ANSWER_TEXT,
                CITATIONS, new BigDecimal("0.90"), true, "local-rag-1.0",
                List.of("KV-0001", "KV-0002"), 120L, null);

        AiAnswerGuard.Verdict verdict = evaluate(conflict);

        assertRefusal(verdict, AiRefusalReason.CONFLICTING_KNOWLEDGE);
        // 冲突时透传模型置信度,便于运营复盘
        assertThat(verdict.confidence()).isEqualByComparingTo(new BigDecimal("0.90"));
    }

    @Test
    @DisplayName("AC-02 适配器自身判定 REFUSE:NO_RELIABLE_KNOWLEDGE")
    void ac02_adapter_refusal_maps_to_no_reliable_knowledge() {
        RagResult refuse = new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null, List.of(),
                RagResult.ZERO_CONFIDENCE, false, "local-rag-1.0", List.of(), 100L, null);

        assertRefusal(evaluate(refuse), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @Test
    @DisplayName("未标记通用回答且引用为空或 null:NO_RELIABLE_KNOWLEDGE")
    void ac02_missing_citations_map_to_no_reliable_knowledge() {
        assertRefusal(evaluate(withCitations(List.of())), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
        assertRefusal(evaluate(withCitations(null)), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @Test
    @DisplayName("AC-02 引用列表含 null 元素:NO_RELIABLE_KNOWLEDGE")
    void ac02_null_citation_element_maps_to_no_reliable_knowledge() {
        List<KnowledgeCitationDto> withNull = Arrays.asList(CITATIONS.get(0), null);

        assertRefusal(evaluate(withCitations(withNull)), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @ParameterizedTest
    @ValueSource(strings = {"0", "0.2", "0.59", "0.95"})
    @DisplayName("任何置信度都必须校验引用仍为当前发布版本")
    void ac02_unpublished_citation_maps_to_no_reliable_knowledge(String confidence) {
        AiAnswerGuard.Verdict verdict =
                AiAnswerGuard.evaluate(perfect(confidence), properties(), false, NONE_PUBLISHED);

        assertRefusal(verdict, AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @Test
    @DisplayName("AC-02 多条引用中任意一条失效即整体拒答,不做部分保留(AI-008)")
    void ac02_any_invalid_citation_refuses_the_whole_answer() {
        KnowledgeCitationDto stale = new KnowledgeCitationDto("KA-0002", "KV-0002",
                "已下线的旧指引", new BigDecimal("0.8000"), "旧流程");
        List<KnowledgeCitationDto> mixed = List.of(CITATIONS.get(0), stale);
        BiPredicate<String, String> onlyFirstPublished =
                (articleId, versionId) -> "KV-0001".equals(versionId);

        AiAnswerGuard.Verdict verdict = AiAnswerGuard.evaluate(
                withCitations(mixed), properties(), false, onlyFirstPublished);

        assertRefusal(verdict, AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @ParameterizedTest
    @ValueSource(strings = {"0", "0.2", "0.59"})
    @DisplayName("有效知识回答不因低置信度拒答，保留审计分数及转人工建议")
    void cited_answer_is_allowed_regardless_of_confidence(String confidence) {
        AiAnswerGuard.Verdict verdict = evaluate(perfect(confidence));

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.answerText()).isEqualTo(ANSWER_TEXT);
        assertThat(verdict.citations()).isEqualTo(CITATIONS);
        assertThat(verdict.refusalReason()).isNull();
        assertThat(verdict.suggestTransfer()).isTrue();
        assertThat(verdict.confidence()).isEqualByComparingTo(new BigDecimal(confidence));
    }

    @Test
    @DisplayName("置信度缺失按 0 留痕，不作为硬拒答条件")
    void null_confidence_defaults_to_zero_without_refusal() {
        RagResult noConfidence = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, ANSWER_TEXT,
                CITATIONS, null, false, "local-rag-1.0", List.of("KV-0001"), 100L, null);

        AiAnswerGuard.Verdict verdict = evaluate(noConfidence);

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.refusalReason()).isNull();
        assertThat(verdict.suggestTransfer()).isTrue();
        assertThat(verdict.confidence()).isEqualByComparingTo(RagResult.ZERO_CONFIDENCE);
    }

    @Test
    @DisplayName("AC-02 正文为空或全空白:NO_RELIABLE_KNOWLEDGE,不返回空答案冒充成功")
    void ac02_blank_answer_text_maps_to_no_reliable_knowledge() {
        RagResult blank = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "   ", CITATIONS,
                new BigDecimal("0.90"), false, "local-rag-1.0", List.of("KV-0001"), 100L, null);
        RagResult nullText = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, null, CITATIONS,
                new BigDecimal("0.90"), false, "local-rag-1.0", List.of("KV-0001"), 100L, null);

        assertRefusal(evaluate(blank), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
        assertRefusal(evaluate(nullText), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    // ------------------------------------------------------------------
    // 五、拒答不变式:AI-004.3 + AI-001「拒答必须给转人工入口」
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-02 所有拒答分支的不变式:answerText 为 null、引用为空、suggestTransfer 恒为 true")
    void ac02_every_refusal_branch_keeps_transfer_entry_open() {
        ConsultationProperties.Ai disabled = properties();
        disabled.setAnswerEnabled(false);

        List<AiAnswerGuard.Verdict> refusals = new ArrayList<>();
        refusals.add(AiAnswerGuard.evaluate(perfect("0.99"), disabled, false, ALL_PUBLISHED));
        refusals.add(AiAnswerGuard.evaluate(perfect("0.99"), properties(), true, ALL_PUBLISHED));
        refusals.add(evaluate(RagResult.degraded(RagStatus.TIMEOUT, "TIMEOUT", 15000L)));
        refusals.add(evaluate(RagResult.degraded(RagStatus.UNAVAILABLE, "CIRCUIT_OPEN", 1L)));
        refusals.add(evaluate(null));
        refusals.add(evaluate(RagResult.degraded(RagStatus.INVALID_RESPONSE, "INVALID_RESPONSE", 80L)));
        refusals.add(evaluate(new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, ANSWER_TEXT,
                CITATIONS, new BigDecimal("0.90"), true, "local-rag-1.0", List.of(), 10L, null)));
        refusals.add(evaluate(withCitations(List.of())));
        refusals.add(AiAnswerGuard.evaluate(perfect("0.95"), properties(), false, NONE_PUBLISHED));
        // 冷启动修订新增:超范围拒答分支(OFF_TOPIC)
        refusals.add(evaluate(offTopicRefusal()));

        assertThat(refusals).hasSize(10);

        Set<AiRefusalReason> reasons = EnumSet.noneOf(AiRefusalReason.class);
        for (AiAnswerGuard.Verdict verdict : refusals) {
            assertThat(verdict.replyType()).isEqualTo(AiReplyType.REFUSE);
            assertThat(verdict.answerText()).isNull();
            assertThat(verdict.citations()).isEmpty();
            assertThat(verdict.suggestTransfer()).isTrue();
            assertThat(verdict.refusalReason()).isNotNull();
            reasons.add(verdict.refusalReason());
        }
        // 分数不再产生 LOW_CONFIDENCE；枚举保留用于协议兼容。
        Set<AiRefusalReason> expected = EnumSet.allOf(AiRefusalReason.class);
        expected.remove(AiRefusalReason.LOW_CONFIDENCE);
        assertThat(reasons).containsExactlyInAnyOrderElementsOf(expected);
    }

    // ------------------------------------------------------------------
    // 五-B、冷启动放宽策略(2026-09-29 修订)
    // ------------------------------------------------------------------

    /** 模型自判超范围(非 IT 办公类)的拒答结果。 */
    private static RagResult offTopicRefusal() {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null, List.of(),
                RagResult.ZERO_CONFIDENCE, false, "local-rag-1.0", List.of(), 100L, null,
                false, true);
    }

    /** 通用能力回答:无命中、无引用、模型基于自身知识作答。 */
    private static RagResult generalAnswer(String confidence) {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, ANSWER_TEXT, List.of(),
                new BigDecimal(confidence), false, "local-rag-1.0", List.of(), 120L, null,
                true, false);
    }

    @Test
    @DisplayName("冷启动:通用能力回答无引用也可放行,但 suggestTransfer 恒为 true")
    void general_answer_without_citations_passes_when_confident() {
        AiAnswerGuard.Verdict verdict = evaluate(generalAnswer("0.90"));

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.answerText()).isEqualTo(ANSWER_TEXT);
        // 通用回答不携带引用(回答来自模型通用能力而非知识库命中)
        assertThat(verdict.citations()).isEmpty();
        assertThat(verdict.refusalReason()).isNull();
        assertThat(verdict.confidence()).isEqualByComparingTo(new BigDecimal("0.90"));
        // 无知识库依据,始终建议转人工入口可见(PRD 8.1)
        assertThat(verdict.suggestTransfer()).isTrue();
    }

    @ParameterizedTest
    @ValueSource(strings = {"0", "0.2", "0.59"})
    @DisplayName("有效通用回答不因低置信度拒答，保留审计分数及转人工建议")
    void general_answer_is_allowed_regardless_of_confidence(String confidence) {
        AiAnswerGuard.Verdict verdict = evaluate(generalAnswer(confidence));

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.answerText()).isEqualTo(ANSWER_TEXT);
        assertThat(verdict.citations()).isEmpty();
        assertThat(verdict.refusalReason()).isNull();
        assertThat(verdict.suggestTransfer()).isTrue();
        assertThat(verdict.confidence()).isEqualByComparingTo(new BigDecimal(confidence));
    }

    @Test
    @DisplayName("冷启动:通用能力回答正文为空时拒答 NO_RELIABLE_KNOWLEDGE,不返回空答案")
    void general_answer_with_blank_text_refuses() {
        RagResult blank = new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "   ", List.of(),
                new BigDecimal("0.90"), false, "local-rag-1.0", List.of(), 100L, null,
                true, false);

        assertRefusal(evaluate(blank), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @Test
    @DisplayName("冷启动:模型自判超范围(非 IT 办公类)拒答 OFF_TOPIC,与知识无依据区分")
    void off_topic_refusal_maps_to_off_topic_reason() {
        AiAnswerGuard.Verdict verdict = evaluate(offTopicRefusal());

        assertRefusal(verdict, AiRefusalReason.OFF_TOPIC);
    }

    @Test
    @DisplayName("冷启动:非超范围的适配器拒答仍归 NO_RELIABLE_KNOWLEDGE,不受新枚举影响")
    void non_off_topic_refusal_still_maps_to_no_reliable_knowledge() {
        RagResult refuse = new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null, List.of(),
                RagResult.ZERO_CONFIDENCE, false, "local-rag-1.0", List.of(), 100L, null,
                false, false);

        assertRefusal(evaluate(refuse), AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @Test
    @DisplayName("冷启动:通用回答不受引用校验影响,即使所有知识都已下线也可放行")
    void general_answer_ignores_citation_validator() {
        AiAnswerGuard.Verdict verdict =
                AiAnswerGuard.evaluate(generalAnswer("0.85"), properties(), false, NONE_PUBLISHED);

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.refusalReason()).isNull();
    }

    // ------------------------------------------------------------------
    // 六、suggestTransfer 阈值(PRD 8.1:转人工入口始终可见)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-01 置信度 0.70(达标但低于 0.75):可答但同时建议转人工")
    void ac01_answer_with_low_confidence_suggests_transfer() {
        AiAnswerGuard.Verdict verdict = evaluate(perfect("0.70"));

        assertThat(verdict.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(verdict.refusalReason()).isNull();
        assertThat(verdict.suggestTransfer()).isTrue();
    }

    @Test
    @DisplayName("AC-01 置信度恰好等于 0.75 边界:不再建议转人工")
    void ac01_confidence_at_suggest_transfer_boundary_does_not_suggest() {
        assertThat(evaluate(perfect("0.75")).suggestTransfer()).isFalse();
        assertThat(evaluate(perfect("0.90")).suggestTransfer()).isFalse();
    }

    // ------------------------------------------------------------------
    // 七、matchesHighRisk(AI-001 高风险主题)
    // ------------------------------------------------------------------

    @Test
    @DisplayName("AC-02 高风险关键词匹配大小写不敏感")
    void ac02_matches_high_risk_is_case_insensitive() {
        List<String> keywords = List.of("删库", "rm -rf", "Root 密码");

        assertThat(AiAnswerGuard.matchesHighRisk("请问怎么 RM -RF / 清理磁盘", keywords)).isTrue();
        assertThat(AiAnswerGuard.matchesHighRisk("root 密码忘了怎么办", keywords)).isTrue();
        assertThat(AiAnswerGuard.matchesHighRisk("生产环境删库了怎么恢复", keywords)).isTrue();
    }

    @Test
    @DisplayName("AC-02 未命中高风险关键词时返回 false,不影响正常问答")
    void ac02_matches_high_risk_returns_false_without_hit() {
        assertThat(AiAnswerGuard.matchesHighRisk("打印机连不上怎么办", List.of("删库", "rm -rf")))
                .isFalse();
    }

    @Test
    @DisplayName("AC-02 空消息、空关键词列表与空白关键词都不构成高风险命中")
    void ac02_matches_high_risk_handles_empty_inputs() {
        assertThat(AiAnswerGuard.matchesHighRisk(null, List.of("删库"))).isFalse();
        assertThat(AiAnswerGuard.matchesHighRisk("", List.of("删库"))).isFalse();
        assertThat(AiAnswerGuard.matchesHighRisk("删库", List.of())).isFalse();
        assertThat(AiAnswerGuard.matchesHighRisk("删库", null)).isFalse();
        assertThat(AiAnswerGuard.matchesHighRisk("任意内容", Arrays.asList(null, "", "   "))).isFalse();
    }
}
