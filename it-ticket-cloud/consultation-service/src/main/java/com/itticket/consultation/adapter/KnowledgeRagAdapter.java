package com.itticket.consultation.adapter;

import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.dto.KnowledgeHit;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.service.KnowledgeQueryService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

/**
 * 本地知识检索型 RAG 适配器(AX-003 RAG 适配器「检索已发布版本、受约束生成」)。
 *
 * <p>一期实现<b>不接入任何外部大模型</b>:回答文本只由命中的已发布知识版本正文裁剪拼装,
 * 不做自由生成,天然满足 AI-001「不得用常识补写未经引用的解决步骤」与
 * RD-006「不生成无来源猜测答案」。供应商、认证协议、连接池等属于 AX-005 未决的部署参数,
 * 本类不预设,替换为外部模型时只需另实现 {@link RagAdapter}。
 *
 * <p>能力边界(AI-001):
 * <ul>
 *   <li>只读 {@code PUBLISHED} 且为当前版本的知识,口径由 {@link KnowledgeQueryService} 统一保证;</li>
 *   <li>有命中 → {@code ANSWER} + 至少一条 {@link KnowledgeCitationDto};</li>
 *   <li>无命中 → {@code REFUSE}、引用为空列表、置信度 0,由上游映射
 *       {@code NO_RELIABLE_KNOWLEDGE} 并给出转人工/直接提单入口;</li>
 *   <li>高风险主题拦截与 {@code ai.answer-enabled} 上线门槛开关(PRD 17.3、RD-006)由上游
 *       {@code AiConsultationService} 在调用本适配器之前判定,本类不重复实现,避免两处口径漂移。</li>
 * </ul>
 *
 * <p>超时、重试、并发上限与断路器不在本类实现,统一由 {@link GuardedRagClient} 施加(RD-003、RD-007);
 * 本类允许向上抛出数据访问异常,由 GuardedRagClient 归类为 {@code UNAVAILABLE} 降级。
 *
 * <p>安全:不记录问题正文、知识正文与检索词(AI-008、RD-013),日志只有条数等元数据。
 */
@Slf4j
@Component
@ConditionalOnProperty(prefix = "itticket.consultation.ai", name = "provider",
        havingValue = "local", matchIfMissing = true)
public class KnowledgeRagAdapter implements RagAdapter {

    /** AI-004.3:引用 snippet 最长 1000。 */
    private static final int SNIPPET_MAX = 1000;
    /** AI-004.3:引用 title 最长 200。 */
    private static final int TITLE_MAX = 200;
    /** AI-004.3:answerText 最长 12000。 */
    private static final int ANSWER_MAX = 12000;
    /** 主答正文裁剪上界,给相关知识清单留出余量。 */
    private static final int ANSWER_PRIMARY_MAX = 4000;
    /** 标题缺失时的占位:Schema 要求 title minLength=1。 */
    private static final String TITLE_PLACEHOLDER = "(未命名知识)";

    /**
     * 知识冲突判据的得分差阈值(归一化后)。
     *
     * <p>写成类常量而非配置项:{@code ConsultationProperties} 不属于本切片的文件归属范围,
     * 不做跨切片改动。需要平台可调时,后续在 {@code ConsultationProperties.Ai} 增加
     * {@code conflictScoreGap} 并从构造器注入即可,判据逻辑无需改动。
     */
    private static final BigDecimal CONFLICT_SCORE_GAP = new BigDecimal("0.05");

    private final KnowledgeQueryService knowledgeQueryService;
    private final ConsultationProperties properties;
    private final RagServiceClient ragServiceClient;

    public KnowledgeRagAdapter(KnowledgeQueryService knowledgeQueryService,
                               ConsultationProperties properties) {
        this.knowledgeQueryService = knowledgeQueryService;
        this.properties = properties;
        this.ragServiceClient = new RagServiceClient(properties);
    }

    @Override
    public RagResult answer(RagQuery query, String requestId) {
        long startNanos = System.nanoTime();
        ConsultationProperties.Ai ai = properties.getAi();
        String modelVersion = ai.getModelVersion();
        if (query == null) {
            return refuse(modelVersion, elapsedMs(startNanos));
        }

        int topK = query.topK() > 0 ? query.topK() : ai.getTopK();
        // priorTurns 只属于会话上下文,本地检索不使用,也不落库、不外发(AI-008)
        boolean remoteRetrieval = "rag-service".equals(ai.getRetrievalProvider());
        List<KnowledgeHit> hits;
        if (remoteRetrieval) {
            RagServiceClient.Retrieval retrieval = ragServiceClient.retrieve(query, requestId);
            if (retrieval.decision() != null) return retrieval.decision();
            hits = retrieval.hits();
        } else if ("mysql".equals(ai.getRetrievalProvider())) {
            hits = knowledgeQueryService.retrieve(query.question(), query.categoryId(), topK);
        } else {
            return RagResult.degraded(RagStatus.UNAVAILABLE, "RAG_NOT_CONFIGURED", elapsedMs(startNanos));
        }
        if (hits.isEmpty()) {
            return refuse(modelVersion, elapsedMs(startNanos));
        }

        List<KnowledgeCitationDto> citations = new ArrayList<>(hits.size());
        List<BigDecimal> scores = new ArrayList<>(hits.size());
        List<String> versionIds = new ArrayList<>(hits.size());
        for (KnowledgeHit hit : hits) {
            BigDecimal score = remoteRetrieval
                    ? BigDecimal.valueOf(hit.getScore()).setScale(RagResult.CONFIDENCE_SCALE, RoundingMode.HALF_UP)
                    : normalize(hit.getScore());
            scores.add(score);
            versionIds.add(hit.getVersionId());
            citations.add(new KnowledgeCitationDto(
                    hit.getArticleId(),
                    hit.getVersionId(),
                    titleOf(hit),
                    score,
                    snippetOf(hit)));
        }

        // 命中已按相关度倒序,首条得分即整体置信度(AI-004.3:取值域 [0,1])
        BigDecimal confidence = scores.get(0);
        boolean conflict = detectConflict(hits, scores);
        String answerText = composeAnswer(hits);

        log.debug("[rag] 本地检索完成 requestId={} sessionId={} hits={} conflict={} costMs={}",
                requestId, query.sessionId(), hits.size(), conflict, elapsedMs(startNanos));

        return new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, answerText,
                List.copyOf(citations), confidence, conflict, modelVersion,
                List.copyOf(versionIds), elapsedMs(startNanos), null);
    }

    /** 无可靠命中:AI-001 必须拒答,不得补写未经引用的步骤。 */
    private static RagResult refuse(String modelVersion, long latencyMs) {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null, List.of(),
                RagResult.ZERO_CONFIDENCE, false, modelVersion, List.of(), latencyMs, null);
    }

    /**
     * 相关度归一化到 [0,1]:{@code s / (s + 1)}。
     *
     * <p>MySQL {@code MATCH ... AGAINST} 的相关度无上界,不能直接当置信度用(AI-004.3 要求 [0,1])。
     * 该函数单调、恒有界、无需知道全库最大分,且对同一批命中保持相对次序;
     * 结果用 {@link BigDecimal} 保留 4 位小数(HALF_UP),与 {@code ai_interaction.confidence
     * DECIMAL(8,4)} 一致,二进制浮点误差不会外泄到接口与存储。
     */
    private static BigDecimal normalize(double rawScore) {
        if (!Double.isFinite(rawScore) || rawScore <= 0d) {
            return RagResult.ZERO_CONFIDENCE;
        }
        BigDecimal raw = BigDecimal.valueOf(rawScore);
        BigDecimal value = raw.divide(raw.add(BigDecimal.ONE), RagResult.CONFIDENCE_SCALE, RoundingMode.HALF_UP);
        if (value.compareTo(BigDecimal.ONE) > 0) {
            return BigDecimal.ONE.setScale(RagResult.CONFIDENCE_SCALE, RoundingMode.UNNECESSARY);
        }
        return value;
    }

    /**
     * 知识冲突近似判据(AI-001「知识冲突必须拒答」)。
     *
     * <p><b>这是一期的近似实现,不是语义级互斥检测</b>:真正判断两篇知识的结论是否互斥需要
     * 语义蕴含模型,属于 AI 评测体系(AI-API-006)后续能力。此处的近似规则为——
     * topK 命中中存在两条满足:同一 {@code categoryId}、归一化得分差小于
     * {@link #CONFLICT_SCORE_GAP}(0.05)、且标题去重后不相同,则判定为疑似冲突。
     * 直觉是:同分类下势均力敌又各自成篇的两份答案,不能由系统替员工挑一份,
     * 应交给上游按 {@code CONFLICTING_KNOWLEDGE} 拒答并转人工。
     *
     * <p>已知偏差:可能把「互补而非互斥」的两篇知识误判为冲突(偏保守,符合 AI-001
     * 宁可拒答不可猜测的取向);也无法发现得分差较大的真实互斥。
     */
    private static boolean detectConflict(List<KnowledgeHit> hits, List<BigDecimal> scores) {
        for (int i = 0; i < hits.size(); i++) {
            for (int j = i + 1; j < hits.size(); j++) {
                String leftCategory = hits.get(i).getCategoryId();
                String rightCategory = hits.get(j).getCategoryId();
                if (leftCategory == null || !leftCategory.equals(rightCategory)) {
                    continue;
                }
                String leftTitle = trimToEmpty(hits.get(i).getTitle());
                String rightTitle = trimToEmpty(hits.get(j).getTitle());
                if (leftTitle.equalsIgnoreCase(rightTitle)) {
                    // 同标题视为同一主题的重复命中,不是冲突
                    continue;
                }
                BigDecimal gap = scores.get(i).subtract(scores.get(j)).abs();
                if (gap.compareTo(CONFLICT_SCORE_GAP) < 0) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * 受约束拼装回答:主答取相关度最高命中的 summary(缺失时取 body),
     * 其余命中只列标题作为线索。全部文本来自已发布知识版本,不做任何生成式改写(AI-001)。
     */
    private static String composeAnswer(List<KnowledgeHit> hits) {
        KnowledgeHit top = hits.get(0);
        String primary = firstNonBlank(top.getSummary(), top.getBody(), top.getTitle(), TITLE_PLACEHOLDER);
        StringBuilder sb = new StringBuilder(truncate(primary, ANSWER_PRIMARY_MAX));
        if (hits.size() > 1) {
            sb.append("\n\n相关知识:");
            for (int i = 1; i < hits.size(); i++) {
                sb.append("\n- ").append(titleOf(hits.get(i)));
            }
        }
        return truncate(sb.toString(), ANSWER_MAX);
    }

    /** 引用标题:AI-004.3 要求 minLength=1、maxLength=200。 */
    private static String titleOf(KnowledgeHit hit) {
        return truncate(firstNonBlank(hit.getTitle(), TITLE_PLACEHOLDER), TITLE_MAX);
    }

    /** 引用片段:AI-004.3 要求 minLength=1、maxLength=1000。 */
    private static String snippetOf(KnowledgeHit hit) {
        return truncate(firstNonBlank(hit.getSummary(), hit.getBody(), hit.getTitle(), TITLE_PLACEHOLDER),
                SNIPPET_MAX);
    }

    private static String firstNonBlank(String... candidates) {
        for (String candidate : candidates) {
            if (candidate != null && !candidate.isBlank()) {
                return candidate.trim();
            }
        }
        return TITLE_PLACEHOLDER;
    }

    private static String trimToEmpty(String value) {
        return value == null ? "" : value.trim();
    }

    private static String truncate(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }

    private static long elapsedMs(long startNanos) {
        return (System.nanoTime() - startNanos) / 1_000_000L;
    }
}
