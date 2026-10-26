package com.itticket.consultation.adapter.analytics;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Python 分析结果 → 链路 {@link RagResult} 的映射。
 *
 * <p>重点在两处语义：分析型回答**不是**「无知识依据的通用建议」（{@code generalAnswer}
 * 必须为 false），以及拒答原因必须原样透出而不是被吞掉。
 */
class AnalyticsClientMappingTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static JsonNode payload(String json) {
        try {
            return JSON.readTree(json);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    @Test
    void 正常作答映射且不标记为无依据() {
        RagResult result = AnalyticsClient.toRagResult(payload("""
                {"replyType":"ANSWER","answerText":"本季度蓝屏 9 单，占 32.1%。","confidence":0.85}
                """));

        assertThat(result.replyType()).isEqualTo(AiReplyType.ANSWER);
        assertThat(result.answerText()).contains("32.1%");
        // 分析型回答的每个数字都由代码从工单实据算出 —— 有硬数据依据，
        // 不能落进工具旁路的「无知识依据」通道。
        assertThat(result.generalAnswer()).isFalse();
        assertThat(result.confidence()).isEqualByComparingTo(new BigDecimal("0.8500"));
        assertThat(result.refusalReason()).isNull();
    }

    @Test
    void 澄清映射为CLARIFY() {
        RagResult result = AnalyticsClient.toRagResult(payload("""
                {"replyType":"CLARIFY","answerText":"你是想让我把这批工单合起来做统计归纳吗？",
                 "confidence":0.5}
                """));

        assertThat(result.replyType()).isEqualTo(AiReplyType.CLARIFY);
    }

    @Test
    void 拒答原因原样透出() {
        RagResult result = AnalyticsClient.toRagResult(payload("""
                {"replyType":"REFUSE","refusalReason":"POLICY_BLOCKED","confidence":0.0}
                """));

        assertThat(result.replyType()).isEqualTo(AiReplyType.REFUSE);
        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.POLICY_BLOCKED);
    }

    @Test
    void 未知拒答原因按无可靠依据处理而不是留null() {
        // 拒答必须带结构化原因（AI-001）；null 混进拒答语义会让运营统计漏掉这一类。
        RagResult result = AnalyticsClient.toRagResult(payload("""
                {"replyType":"REFUSE","refusalReason":"SOMETHING_NEW"}
                """));

        assertThat(result.refusalReason()).isEqualTo(AiRefusalReason.NO_RELIABLE_KNOWLEDGE);
    }

    @Test
    void 有作答类型却没有正文视为结构异常() {
        // 不返回一段空回答让员工看到"AI 什么都没说" —— 那是协议问题，不是业务结果。
        assertThatThrownBy(() -> AnalyticsClient.toRagResult(payload("""
                {"replyType":"ANSWER","confidence":0.5}
                """))).isInstanceOf(DependencyFailure.class);
    }

    @Test
    void 置信度缺失或非数值归零() {
        RagResult result = AnalyticsClient.toRagResult(payload("""
                {"replyType":"REFUSE","refusalReason":"NO_RELIABLE_KNOWLEDGE"}
                """));

        assertThat(result.confidence()).isEqualByComparingTo(RagResult.ZERO_CONFIDENCE);
    }

    @Test
    void 降级原因写入模型版本位供排查() {
        // 降级原因要能被盘面看见：只看到一句"答复是模板"猜不出哪一环出的问题。
        RagResult result = AnalyticsClient.toRagResult(payload("""
                {"replyType":"ANSWER","answerText":"统计口径：2026 Q4。","confidence":0.7,
                 "degradedReason":"MODEL_NOT_CONFIGURED"}
                """));

        assertThat(result.modelVersion()).isEqualTo("MODEL_NOT_CONFIGURED");
    }

    @Test
    void 不引用任何知识版本() {
        // 分析不检索知识库，引用列表必须为空 —— 有引用反而说明链路走错了。
        RagResult result = AnalyticsClient.toRagResult(payload("""
                {"replyType":"ANSWER","answerText":"结论。","confidence":0.8}
                """));

        assertThat(result.citations()).isEmpty();
        assertThat(result.retrievedVersionIds()).isEmpty();
    }
}