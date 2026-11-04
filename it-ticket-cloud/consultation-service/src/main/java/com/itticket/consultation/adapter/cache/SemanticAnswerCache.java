package com.itticket.consultation.adapter.cache;

import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.adapter.embedding.EmbeddingClient;
import com.itticket.consultation.config.ConsultationProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.function.BiPredicate;

/**
 * 进程内语义答案缓存(讲义思想 + 本项目治理):条目 = 归一化问题向量 → 不可变 RagResult。
 *
 * 正确性模型:缓存只是加速层,失效锚定在 versionCheck(装配期注入的
 * KnowledgeQueryService::isPublishedCurrentVersion,锁外逐条复核 citations 的
 * versionId)。失效即驱逐并按真实未命中穿透——不存在「过期缓存放行」。
 *
 * 写准入:仅 SUCCESS + ANSWER + citations 非空 + 非 generalAnswer + errorClass 为空;
 * 拒答 / CLARIFY / 通用回答 / 降级没有版本失效锚点(或没有模型成本),永不入缓存;
 * 带工单草稿的结果承载提问者具体环境,跨用户重放即泄露,同样永不入缓存。
 * 追问(priorTurns 非空)不读不写——语义缓存只对独立初问有定义。
 *
 * 并发:容器由方法级 synchronized 保护;嵌入调用(网络)在锁外执行,不持锁做远程调用。
 * 不同 embedding 模型的向量不可比,条目按模型名分命名空间。匹配一律走余弦相似度,
 * 问题文本仅以 trim+折叠空白规范化用于展示与去重审计。
 */
public final class SemanticAnswerCache {

    private static final Logger log = LoggerFactory.getLogger(SemanticAnswerCache.class);

    private static final int RECENT_SIMILARITIES_CAP = 50;

    private final boolean enabled;
    private final double threshold;
    private final int maxEntries;
    private final long ttlSeconds;
    private final long minWriteIntervalSeconds;
    private final String embeddingModel;
    private final EmbeddingClient embeddings;
    private final BiPredicate<String, String> versionCheck;
    private final Clock clock;

    private final List<Entry> entries = new ArrayList<>();
    private long hits;
    private long realMisses;
    private long depFailures;
    private long evictionsTtl;
    private long evictionsLru;
    private long evictionsSentinel;
    private double maxHitSimilarity;
    private final ArrayDeque<Double> recentSimilarities = new ArrayDeque<>();

    /** 停用实例:enabled=false 默认装配与测试占位,lookup 恒空、write 直通无副作用。 */
    public static SemanticAnswerCache disabled() {
        return new SemanticAnswerCache(new ConsultationProperties.Ai.Cache(),
                (text, context) -> { throw DependencyFailure.invalid(); }, (a, v) -> true, Clock.systemUTC());
    }

    public SemanticAnswerCache(ConsultationProperties.Ai.Cache config, EmbeddingClient embeddings,
                               BiPredicate<String, String> versionCheck, Clock clock) {
        this.enabled = config.isEnabled();
        this.threshold = config.getThreshold();
        this.maxEntries = Math.max(1, config.getMaxEntries());
        this.ttlSeconds = config.getTtlSeconds();
        this.minWriteIntervalSeconds = config.getMinWriteIntervalSeconds();
        this.embeddingModel = config.getEmbeddingModel() == null ? "" : config.getEmbeddingModel();
        this.embeddings = embeddings;
        this.versionCheck = versionCheck;
        this.clock = clock;
    }

    /**
     * 查缓存。停用与追问直接穿透(不计任何数);嵌入依赖失败按 depFailures 计并 WARN
     * 后穿透,缓存故障不升级为会话故障。锁内选最佳匹配并留出哨兵复核所需的条目快照,
     * 哨兵在锁外逐条对 versionCheck 复核;未过哨兵的条目驱逐 + 真实未命中。
     */
    public Optional<CachedAnswer> lookup(RagQuery query, RagCallContext context) {
        if (!enabled || !query.priorTurns().isEmpty()) {
            return Optional.empty();
        }
        String question = normalize(query.question());
        if (question.isEmpty()) {
            return Optional.empty(); // 空白问题不嵌入不计数:上游域门禁会先拒,这里只兜底
        }
        float[] vector;
        try {
            vector = embeddings.embed(question, context);
        } catch (DependencyFailure failure) {
            synchronized (this) { depFailures++; }
            log.warn("语义缓存嵌入依赖失败,按未命中穿透: requestId={} errorClass={}",
                    context.requestId(), failure.getMessage());
            return Optional.empty();
        }
        Entry snapshot = acquireHit(vector, query.categoryId(), query.assetId());
        if (snapshot == null) {
            return Optional.empty();
        }
        boolean current;
        try {
            current = citationsStillCurrent(snapshot);
        } catch (RuntimeException failure) {
            synchronized (this) { depFailures++; }
            log.warn("语义缓存哨兵复核异常,按未命中穿透: requestId={} error={}",
                    context.requestId(), failure.getMessage());
            return Optional.empty();
        }
        if (!current) {
            evict(snapshot);
            synchronized (this) { realMisses++; }
            return Optional.empty();
        }
        synchronized (this) {
            hits++;
            snapshot.live.hitCount++;
            snapshot.live.lastAccessed = clock.instant();
            recordSimilarityLocked(snapshot.lastSimilarity);
        }
        return Optional.of(new CachedAnswer(snapshot.result, snapshot.lastSimilarity));
    }

    /**
     * 写缓存。准入条件见类注释;同义问法(≥threshold)原位替换而非追加,
     * minWriteInterval 窗口内不刷新;超上限先逐出最久未访问条目(LRU)。
     */
    public void write(RagQuery query, RagCallContext context, RagResult result) {
        if (!enabled || !admissible(result) || !query.priorTurns().isEmpty()) {
            return;
        }
        float[] vector;
        try {
            vector = embeddings.embed(normalize(query.question()), context);
        } catch (DependencyFailure failure) {
            synchronized (this) { depFailures++; }
            log.warn("语义缓存写入嵌入失败: errorClass={}", failure.getMessage());
            return;
        }
        Instant now = clock.instant();
        synchronized (this) {
            purgeExpired();
            Entry replaceable = bestMatch(vector, query.categoryId(), query.assetId());
            if (replaceable != null) {
                if (minWriteIntervalSeconds > 0
                        && Duration.between(replaceable.lastAccessed, now).toSeconds() < minWriteIntervalSeconds) {
                    return;
                }
                replaceable.questionText = normalize(query.question());
                replaceable.questionVector = vector;
                replaceable.result = result;
                replaceable.createdAt = now;
                replaceable.lastAccessed = now;
                replaceable.hitCount = 0;
                replaceable.lastSimilarity = 0.0;
                return;
            }
            if (entries.size() >= maxEntries) {
                Entry oldest = entries.get(0);
                for (Entry candidate : entries) {
                    if (candidate.lastAccessed.isBefore(oldest.lastAccessed)) {
                        oldest = candidate;
                    }
                }
                entries.remove(oldest);
                evictionsLru++;
            }
            entries.add(new Entry(normalize(query.question()), vector, embeddingModel,
                    query.categoryId(), query.assetId(), result, now, now));
        }
    }

    /** 运行快照(只读,给管理员审计端点)。hitRate=hits/(hits+realMisses),分母 0 取 0。 */
    public synchronized CacheStats stats() {
        double rate = (hits + realMisses) == 0 ? 0.0 : (double) hits / (hits + realMisses);
        return new CacheStats(hits, realMisses, depFailures, evictionsTtl, evictionsLru,
                evictionsSentinel, entries.size(), rate, maxHitSimilarity,
                List.copyOf(recentSimilarities));
    }

    /** 锁内选出并触碰最佳匹配,返回供锁外哨兵复核的条目快照;无匹配计真实未命中。 */
    private synchronized Entry acquireHit(float[] vector, String categoryId, String assetId) {
        purgeExpired();
        Entry best = bestMatch(vector, categoryId, assetId);
        if (best == null) {
            realMisses++;
            return null;
        }
        // 触碰(hitCount/lastAccessed)后移到哨兵通过之后:过期条目不再被失败地查询
        // 刷新 LRU 体温或虚增命中计数。快照携带 live 引供哨兵通过后回触与身份驱逐。
        Entry snapshot = new Entry(best.questionText, best.questionVector, best.namespace,
                best.categoryId, best.assetId, best.result, best.createdAt, best.lastAccessed);
        snapshot.lastSimilarity = best.lastSimilarity; // bestMatch 已写入本次命中余弦
        snapshot.live = best;
        return snapshot;
    }

    /** 哨兵:逐条 citations 的 articleId+versionId 对当前发布版本复核(Task 4 细测)。 */
    private boolean citationsStillCurrent(Entry snapshot) {
        List<com.itticket.consultation.dto.KnowledgeCitationDto> citations =
                snapshot.result.citations();
        if (citations == null || citations.isEmpty()) {
            return false;
        }
        for (com.itticket.consultation.dto.KnowledgeCitationDto citation : citations) {
            if (citation.versionId() == null || citation.articleId() == null) {
                return false;
            }
            if (!versionCheck.test(citation.articleId(), citation.versionId())) {
                return false;
            }
        }
        return true;
    }

    private synchronized void evict(Entry snapshot) {
        boolean removed = entries.removeIf(entry -> entry == snapshot.live);
        if (removed) {
            evictionsSentinel++;
        }
    }

    private boolean admissible(RagResult result) {
        return result.status() == RagStatus.SUCCESS
                && result.replyType() == com.itticket.consultation.enums.AiReplyType.ANSWER
                && result.refusalReason() == null
                && result.errorClass() == null
                && !result.generalAnswer()
                && !result.retryableFailure()
                && result.answerText() != null && !result.answerText().isBlank()
                && result.citations() != null && !result.citations().isEmpty()
                && result.citations().stream().allMatch(c -> c.versionId() != null)
                && result.ticketDraft() == null;
    }

    private void purgeExpired() {
        Instant cutoff = clock.instant().minusSeconds(ttlSeconds);
        Iterator<Entry> iterator = entries.iterator();
        while (iterator.hasNext()) {
            if (iterator.next().createdAt.isBefore(cutoff)) {
                iterator.remove();
                evictionsTtl++;
            }
        }
    }

    private Entry bestMatch(float[] vector, String categoryId, String assetId) {
        Entry best = null;
        double bestSimilarity = -1.0;
        for (Entry entry : entries) {
            if (!entry.namespace.equals(embeddingModel)) {
                continue;
            }
            if (!scopeMatches(entry, categoryId, assetId)) {
                continue;
            }
            double similarity = cosine(vector, entry.questionVector);
            if (similarity >= threshold && similarity > bestSimilarity) {
                best = entry;
                bestSimilarity = similarity;
            }
        }
        if (best != null) {
            best.lastSimilarity = bestSimilarity;
        }
        return best;
    }

    /** 查询侧 category/assetId 为 null 视为通配(不限作用域),非 null 时要求相等。 */
    private boolean scopeMatches(Entry entry, String categoryId, String assetId) {
        boolean categoryOk = categoryId == null || Objects.equals(entry.categoryId, categoryId);
        boolean assetOk = assetId == null || Objects.equals(entry.assetId, assetId);
        return categoryOk && assetOk;
    }

    private void recordSimilarityLocked(double similarity) {
        if (similarity > maxHitSimilarity) {
            maxHitSimilarity = similarity;
        }
        recentSimilarities.addLast(similarity);
        while (recentSimilarities.size() > RECENT_SIMILARITIES_CAP) {
            recentSimilarities.removeFirst();
        }
    }

    private static double cosine(float[] a, float[] b) {
        if (a.length != b.length) {
            return 0.0;
        }
        double sum = 0.0;
        for (int i = 0; i < a.length; i++) {
            sum += (double) a[i] * b[i];
        }
        return sum;
    }

    private static String normalize(String text) {
        if (text == null) {
            return "";
        }
        return text.strip().replaceAll("\\s+", " ");
    }

    /** 条目;lookup 命中时以它为模板在锁内拷贝快照,避免锁外读到可变状态。 */
    private static final class Entry {
        String questionText;
        float[] questionVector;
        final String namespace;
        String categoryId;
        String assetId;
        RagResult result;
        Instant createdAt;
        Instant lastAccessed;
        long hitCount;
        double lastSimilarity;
        /** 仅快照携带:指向锁内存活条目,供哨兵通过后回触与身份驱逐;真实条目恒 null。 */
        Entry live;

        Entry(String questionText, float[] questionVector, String namespace, String categoryId,
              String assetId, RagResult result, Instant createdAt, Instant lastAccessed) {
            this.questionText = questionText;
            this.questionVector = questionVector;
            this.namespace = namespace;
            this.categoryId = categoryId;
            this.assetId = assetId;
            this.result = result;
            this.createdAt = createdAt;
            this.lastAccessed = lastAccessed;
        }
    }
}
