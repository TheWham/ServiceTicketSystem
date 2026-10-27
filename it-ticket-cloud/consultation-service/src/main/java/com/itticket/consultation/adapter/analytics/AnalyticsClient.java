package com.itticket.consultation.adapter.analytics;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URI;
import java.util.List;
import java.util.Map;

/**
 * Python analytics_service 客户端（跨工单宏观聚合归纳，端口 8340）。
 *
 * <p><b>与 {@code PythonAgentClient} 的本质区别</b>：agent 是让模型决定「调哪个工具、
 * 调几次」；分析链路是**确定性节点链** —— 聚合维度、占比算法、备件建议条目全部固化在
 * Python 侧的词表与代码里，模型只负责最后的措辞。所以本类不做 ReAct 循环，一次请求即终局。
 *
 * <p><b>为什么分析型回答标记 {@code generalAnswer=false}</b>：工具意图旁路的作答被标成
 * {@code generalAnswer=true} 走「无知识依据的通用建议」通道（{@code AiAnswerGuard} 第 7 条），
 * 而分析型回答恰好相反 —— 它的每个数字都由代码从工单实据算出，是**有硬数据依据**的。
 * 塞进那条通道是语义污染，会让守卫与前端都用错误的假设解释这段回答。
 *
 * <p><b>失败语义</b>：传输层失败与业务失败都收敛为 {@link DependencyFailure}，
 * 由 {@code ComposedRagAdapter} 统一转结构化拒答 —— 与既有链路一致，不静默回退。
 */
public final class AnalyticsClient {

    private static final Logger log = LoggerFactory.getLogger(AnalyticsClient.class);

    /**
     * 分析要扫时间窗内的全部工单、再让归因模型写一段叙事，比单轮问答重得多。
     *
     * <p>实测数据：本端点配的 `deepseek-v4-flash` 实际是推理模型，归因叙事单次要
     * 6000~10000 个输出 token（其中 94% 是推理），端到端 43~95 秒。
     * 沿用 agent 的 60s 会把正常的一次分析误杀 —— 所以这里给到 180s，
     * 与 Python 侧 `ANALYTICS_LLM_TIMEOUT` 对齐。
     */
    private static final long REQUEST_TIMEOUT_MS = 180000L;

    private final ConsultationProperties.Analytics analytics;
    private final DependencyHttpClient http;
    private final ObjectMapper json = new ObjectMapper();

    public AnalyticsClient(ConsultationProperties properties, DependencyHttpClient http) {
        this.analytics = properties.getAi().getAnalytics();
        this.http = http;
    }

    /** 是否启用（开关打开且配了 Python analytics_service 地址）。 */
    public boolean enabled() {
        return analytics.isEnabled()
                && analytics.getServiceBaseUrl() != null
                && !analytics.getServiceBaseUrl().isBlank();
    }

    /**
     * 跑一次分析链路，返回可直接使用的 {@link RagResult}。
     *
     * <p>注意：这里**只带回答正文**。统计明细（{@code analyticsFacts}）不经过 RagResult，
     * 由 {@link #queryPayload} 供前端专用接口取用 —— 两者共用一个后端口径，
     * 前端表格读 facts，不读模型写的正文。
     */
    public RagResult analyze(RagQuery query, RagCallContext context) {
        JsonNode data = queryPayload(query.question(), query.caller().userId(),
                query.caller().role(), context, UPSTREAM_ANALYTICS);
        return toRagResult(data);
    }

    /**
     * 上游已定性的意图 —— **客服入口专用的传值**。
     *
     * <p>客服入口的"是不是分析题"由 Java 分类器判定（判为分析型才会调到本类），
     * 所以如实告诉 Python"上游已定性"：Python 侧据此锁死意图、不再翻案。分类器误判
     * 时由上游负责，不在下游二次裁决 —— 否则同一个问题会在两处各被判一次，还给出
     * 不同结论。
     *
     * <p>看板入口**不传这个值**，见 {@link #queryPayload} 的说明。
     */
    private static final String UPSTREAM_ANALYTICS = "ANALYTICS";

    /**
     * 取完整负载（含 analyticsFacts），供前端分析看板使用。
     *
     * <p>{@code upstreamIntent} 传空表示**不预设**：由 Python 自己判定是不是分析型问题，
     * 判为非分析型就熔断（{@code refusalReason=OUT_OF_SCOPE}）并引导去智能客服。
     * 看板入口刻意走这条路 —— 工程师进了统计工作台也可能问一个具体故障，那种问题
     * 不该被硬当成统计题作答（实测踩到过：问"VPN 连不上怎么办"会收到一份 29 张工单的
     * 季度分布报告，正是这条链路要消灭的答非所问）。
     */
    public JsonNode queryPayload(String question, String userId, String role,
                                 RagCallContext context, String upstreamIntent) {
        if (!enabled()) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "ANALYTICS_DISABLED", false);
        }
        ObjectNode body = json.createObjectNode().put("question", question == null ? "" : question)
                .put("userId", userId == null ? "" : userId)
                .put("role", role == null ? "" : role)
                .put("requestId", context == null ? "" : context.requestId())
                // 上游定性信号。空串＝不预设，交由 Python 判定（判非分析型即熔断）
                .put("upstreamIntent", upstreamIntent == null ? "" : upstreamIntent);

        String base = analytics.getServiceBaseUrl().replaceAll("/+$", "");
        JsonNode root = http.post(URI.create(base + "/api/v1/analytics/query"), body,
                Map.of("X-User-Id", userId == null ? "" : userId,
                        "X-User-Role", role == null ? "" : role),
                context, REQUEST_TIMEOUT_MS);
        if (!root.path("code").isIntegralNumber()) throw DependencyFailure.invalid();
        if (root.path("code").intValue() != 0) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "ANALYTICS_BUSINESS_ERROR", false);
        }
        JsonNode data = root.path("data");
        if (!data.isObject()) throw DependencyFailure.invalid();
        return data;
    }

    /** 把 Python 的分析结果映射成链路统一的 RagResult。 */
    static RagResult toRagResult(JsonNode data) {
        String text = text(data, "answerText");
        AiReplyType replyType = replyTypeOf(text(data, "replyType"));
        AiRefusalReason reason = refusalReasonOf(text(data, "refusalReason"));
        if (text.isBlank() && replyType == AiReplyType.ANSWER) {
            // 有 replyType 却没有正文：结构不对，交给上游按依赖失败处理，
            // 不返回一段空回答让员工看到"AI 什么都没说"。
            throw DependencyFailure.invalid();
        }
        BigDecimal confidence = confidenceOf(data.path("confidence"));
        // 分析型回答有硬数据依据 → generalAnswer=false（见类注释）
        return new RagResult(RagStatus.SUCCESS, replyType, text, List.of(), confidence,
                reason, text(data, "degradedReason").isBlank() ? null : text(data, "degradedReason"),
                List.of(), 0, null, false, false, null);
    }

    private static AiReplyType replyTypeOf(String raw) {
        return switch (raw == null ? "" : raw.trim().toUpperCase()) {
            case "ANSWER", "NOT_ANALYTICS" -> AiReplyType.ANSWER;
            case "CLARIFY" -> AiReplyType.CLARIFY;
            case "REFUSE" -> AiReplyType.REFUSE;
            default -> AiReplyType.REFUSE;
        };
    }

    private static AiRefusalReason refusalReasonOf(String raw) {
        if (raw == null || raw.isBlank()) return null;
        try {
            return AiRefusalReason.valueOf(raw.trim().toUpperCase());
        } catch (IllegalArgumentException unknown) {
            // 不认识的拒答原因按「无可靠依据」处理（保守），而不是把 null 混进拒答语义
            log.warn("[分析] 未知拒答原因 '{}'，按 NO_RELIABLE_KNOWLEDGE 处理", raw);
            return AiRefusalReason.NO_RELIABLE_KNOWLEDGE;
        }
    }

    private static BigDecimal confidenceOf(JsonNode node) {
        if (!node.isNumber()) return RagResult.ZERO_CONFIDENCE;
        return BigDecimal.valueOf(node.asDouble())
                .setScale(RagResult.CONFIDENCE_SCALE, RoundingMode.HALF_UP);
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.path(field);
        return value.isTextual() ? value.textValue() : "";
    }
}