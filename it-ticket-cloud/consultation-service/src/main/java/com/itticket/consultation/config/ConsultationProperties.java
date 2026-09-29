package com.itticket.consultation.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** 咨询域可配置项。默认值取自 PRD 与 spec,平台管理员可在允许范围内覆盖。 */
@Data
@ConfigurationProperties(prefix = "itticket.consultation")
public class ConsultationProperties {

    /** 旧角色值 → DM-002 RoleCode(AX-005 未决项的一期默认映射)。 */
    private Map<String, String> roleMapping = new LinkedHashMap<>();

    /** 幂等记录保留时长(RD-002 要求有过期时间)。 */
    private int idempotencyTtlHours = 24;

    private Sla sla = new Sla();
    private Transfer transfer = new Transfer();
    private Lifecycle lifecycle = new Lifecycle();
    private Ai ai = new Ai();

    @Data
    public static class Sla {
        private String calendarId = "DEFAULT";
        /** PRD 11.2:人工咨询 10 个工作分钟。 */
        private long responseTargetWorkSeconds = 600;
        /** PRD 11.3:响应 SLA 在第 8 个工作分钟提醒。 */
        private long nearBreachWorkSeconds = 480;
    }

    @Data
    public static class Transfer {
        /** RD-005:每名候选人最多尝试一次,达到上限进异常队列。 */
        private int maxCandidates = 8;
        /** PRD 12.2:活跃人工咨询权重。 */
        private int consultationLoadWeight = 2;
    }

    @Data
    public static class Lifecycle {
        /** SM-CONSULT-001:RESOLVED 24 小时内可恢复。 */
        private int reopenWindowHours = 24;
        /** PRD 8.3:员工断开且 10 分钟未回复才允许自动解决。 */
        private int autoResolveIdleMinutes = 10;
    }

    @Data
    public static class Ai {
        /** PRD 17.3 / RD-006:评测未达门槛时关闭 AI 综合回答,其余功能不受影响。 */
        private boolean answerEnabled = true;

        /**
         * 生成侧供应商。
         * <ul>
         *   <li>{@code openai-compatible}:调用 OpenAI 兼容端点做受约束生成;</li>
         *   <li>{@code local}:不调外部模型,只按检索结果拼装答案(离线/演示/评测未上线时使用)。</li>
         * </ul>
         * 无论哪种,检索都只读 PUBLISHED 知识,生成都必须落在检索到的资料上(AI-001)。
         */
        private String provider = "local";

        /** OpenAI 兼容端点的基址,例如 https://.../compatible-mode/v1(不含 /chat/completions)。 */
        private String baseUrl;

        /**
         * 访问凭据。AX-007:供应商 URL 与凭据必须从加密配置读取,
         * 不得硬编码在代码或提交到仓库的配置里。生产从环境变量或配置中心注入。
         */
        private String apiKey;

        /** 模型 ID,由端点决定。 */
        private String model = "qwen3-vl-32b-thinking";

        /**
         * 生成 token 上限。
         *
         * <p>注意:thinking 类模型把内部推理 token 也计入该上限。实测该端点上
         * {@code qwen3-vl-32b-thinking} 一次小规模 RAG 问答要消耗约 500 个推理 token,
         * 上限给小了会出现「推理占满、content 为空」——表现为无声的无效输出。
         * 因此默认给足余量,不要按 answerText 的 12000 字符上限倒推。
         */
        private int maxOutputTokens = 8192;

        /** 受约束问答不需要发散,固定为 0 保证同一问题可复现(AI 评测要求可重复)。 */
        private double temperature = 0.0;

        private String modelVersion = "local-rag-1.0";
        private int topK = 3;
        /** 低于该置信度必须拒答(AI-001)。 */
        private BigDecimal minConfidence = new BigDecimal("0.60");
        /** 低于该置信度即便可答也建议转人工。 */
        private BigDecimal suggestTransferBelowConfidence = new BigDecimal("0.75");
        /** RD-003:首段 5 秒。 */
        private long firstTokenTimeoutMs = 5000;
        /** RD-003:完整 15 秒。 */
        private long requestTimeoutMs = 15000;
        /** RD-003:同一请求最多重试 1 次,即最多 2 次尝试。 */
        private int maxAttempts = 2;
        /** RD-007:独立并发上限,满载立即降级不排队。 */
        private int maxConcurrency = 8;
        private int circuitFailureThreshold = 5;
        private long circuitOpenMillis = 30000;
        private int circuitHalfOpenSuccessThreshold = 3;
        /** AI-001:高风险主题关键词,命中即拒答并引导转人工。 */
        private List<String> highRiskKeywords = new java.util.ArrayList<>();
    }
}
