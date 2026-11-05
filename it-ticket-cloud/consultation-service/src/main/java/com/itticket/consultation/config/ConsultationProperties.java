package com.itticket.consultation.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
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
         * 检索都只读 PUBLISHED 知识；模型模式也可给不带知识引用的通用 IT 回答。
         */
        private String provider = "local";
        private long ragRequestTimeoutMs = 5000;
        private BigDecimal localRetrievalMinScore = new BigDecimal("0.60");

        /** 检索来源与生成供应商分开：rag-service 为混合检索，mysql 为显式兼容模式。 */
        private String retrievalProvider = "rag-service";
        /** 服务内网地址；调用时透传已认证主体，不发送模型凭据。 */
        private String ragBaseUrl = "http://127.0.0.1:8302";
        private long retrievalTimeoutMs = 20000;
        /** 单条引用门槛，与 RAG_CONFIDENCE_THRESHOLD 保持一致，防止批次可靠性放大弱命中。 */
        private BigDecimal ragCitationMinScore = new BigDecimal("0.70");

        /** OpenAI 兼容端点的基址,例如 https://.../compatible-mode/v1(不含 /chat/completions)。 */
        private String baseUrl;

        /**
         * 访问凭据。AX-007:供应商 URL 与凭据必须从加密配置读取,
         * 不得硬编码在代码或提交到仓库的配置里。生产从环境变量或配置中心注入。
         */
        private String apiKey;

        /** 模型 ID,由端点决定。 */
        private String model = "deepseek-v4-flash";

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
        /** Maximum persisted history messages; nonpositive uses 12, hard cap 40. */
        private int contextMaxMessages = 12;
        /** Total history UTF-16 characters; nonpositive uses 12000, hard cap 32000. */
        private int contextMaxChars = 12000;
        /** 旧配置兼容项，不再作为有效回答的拒答门槛；置信度仅用于审计和转人工建议。 */
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

        /** 图扩展邻居准入谓词参数,默认与 python 侧 rag_pipeline.config 一致。 */
        private GraphExpansion graphExpansion = new GraphExpansion();

        /** Function Calling 智能体配置(生成侧下沉到 Python agent_service)。 */
        private Agent agent = new Agent();

        /** 跨工单分析链路配置(默认关闭)。 */
        private Analytics analytics = new Analytics();

        /** 语义答案缓存(带知识版本哨兵),默认关闭。 */
        private Cache cache = new Cache();

        /** 流式回答(T-6):入端点常在,开关只决定"生成期间增量令牌上屏"还是"整段单发"。 */
        private Streaming streaming = new Streaming();

        /**
         * 语义答案缓存配置。正确性锚定在 MySQL 知识版本哨兵上:缓存条目必须携带非空
         * citations(检索到的知识版本号),命中出缓存前逐条对当前版本复核,失效即驱逐。
         * 不同 embedding 模型的向量彼此不可比,条目按模型名分命名空间。
         */
        @Data
        public static class Cache {
            /** 总开关。默认关闭:关闭时与引入缓存前的行为完全一致。 */
            private boolean enabled = false;
            /** 问题向量余弦相似度命中门槛;低于 0.90 的取值在装配期被拒绝(语义漂移风险)。 */
            private double threshold = 0.93;
            /** 条目上限(进程内有界结构,LRU 逐出)。 */
            private int maxEntries = 500;
            /** 兜底 TTL:命中条目最长存活 7 天,防止知识后补后旧答案长期不被哨兵驱逐。 */
            private long ttlSeconds = 604800;
            /** 嵌入模型 ID;enabled=true 时必填,否则启动失败(不提供半启用状态)。 */
            private String embeddingModel;
            /** OpenAI 兼容嵌入端点基址(不含 /embeddings);为空回退 ai.base-url。 */
            private String embeddingBaseUrl;
            /** 嵌入调用时长上限,计入请求统一超时预算。 */
            private long embeddingTimeoutMs = 1000;
            /** 同条目刷新去抖窗口(秒);0 表示每次都刷新。 */
            private long minWriteIntervalSeconds = 0;
        }
    }

    /**
     * 图扩展邻居准入谓词:五条件全满足才收,任一不满足仅丢该扩展条目,不影响拒答门。
     * 默认值与 python 侧 rag_pipeline.config.ExpansionConfig 一致。
     */
    @Data
    public static class GraphExpansion {
        /** 白名单;REPLACES 与共指边在工业共识上不是列证依据,永不入场。 */
        private LinkedHashSet<String> edgeWhitelist = new LinkedHashSet<>(
                Arrays.asList("SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES"));
        /** 扩展条目分下限。 */
        private BigDecimal scoreFloor = new BigDecimal("0.10");
        /** 单个源卡可携带的邻居上限。 */
        private int maxNeighbors = 2;
    }

    /**
     * Function Calling 智能体配置。默认关闭;开启后生成层改为调 Python `agent_service`
     * (ReAct 循环 + 白名单工具),关闭时维持本地单轮「强制 JSON」生成(现状不变)。
     */
    @Data
    public static class Agent {
        private boolean enabled = false;
        /** Python agent_service 基址,如 http://127.0.0.1:8320。 */
        private String serviceBaseUrl;
        /** ticket-service 内部接口基址(供「确认建单」回写工单;工单是 ticket-service 事实源)。 */
        private String ticketServiceBaseUrl;
    }

    /**
     * 跨工单分析链路配置。默认关闭;开启后判定为 ANALYTICS 的请求改调 Python
     * `analytics_service`(确定性聚合 + 归因叙事)。
     *
     * <p>与 {@link Agent} 分开配而不是合并成一个开关:两者是**不同的链路** ——
     * 分析走确定性聚合、不做 function call,端口、超时与失败语义都不同。
     * 合并会让「想开分析但不想开 ReAct」这种合理组合变得不可表达。
     */
    @Data
    public static class Analytics {
        private boolean enabled = false;
        /** Python analytics_service 基址,如 http://127.0.0.1:8340。 */
        private String serviceBaseUrl;
    }

    /** 流式回答开关与保活节奏(T-6)。 */
    @Data
    public static class Streaming {
        /** false=入/写与旧同步端点完全一致(生成期间令牌不上屏,整段单发后 final)。 */
        private boolean enabled = false;
        /** SSE 空转帧间隔;排队与生成期间都有,兼作断连探测。 */
        private long keepAliveMillis = 15_000;
    }
}
