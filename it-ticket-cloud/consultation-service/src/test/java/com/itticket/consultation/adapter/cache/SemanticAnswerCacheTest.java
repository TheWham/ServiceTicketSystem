package com.itticket.consultation.adapter.cache;

import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.adapter.RagCaller;
import com.itticket.consultation.adapter.embedding.EmbeddingClient;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;

/**
 * 语义缓存写路径准入门槛:只有「SUCCESS + ANSWER + citations 非空 + 非 generalAnswer +
 * 非降级」的实证答案才可入缓存;拒答/澄清/通用回答/降级是系统即时状态的判断,
 * 无 versionId 失效锚点,固化它们等于把知识缺口或故障快照焊死到 TTL。
 * 写入成功不产生任何计数(计数只发生在 lookup)。
 */
class SemanticAnswerCacheTest {

    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");

    /** 可拨动的时钟(TTL 测试)。 */
    private static final class SettableClock extends Clock {
        private volatile Instant now = Instant.parse("2026-11-04T10:00:00Z");
        void advanceSeconds(long seconds) { now = now.plusSeconds(seconds); }
        @Override public ZoneId getZone() { return ZONE; }
        @Override public Clock withZone(ZoneId zone) { return this; }
        @Override public Instant instant() { return now; }
    }

    private final AtomicReference<float[]> nextVector = new AtomicReference<>(new float[]{1f, 0f});
    private final AtomicLong embedCalls = new AtomicLong();
    private final EmbeddingClient vectors = (text, context) -> {
        embedCalls.incrementAndGet();
        float[] v = nextVector.get();
        float norm = 0;
        for (float c : v) norm += c * c;
        norm = (float) Math.sqrt(norm);
        float[] out = new float[v.length];
        for (int i = 0; i < v.length; i++) out[i] = v[i] / norm;
        return out;
    };
    private final SettableClock clock = new SettableClock();

    private SemanticAnswerCache cache(ConsultationProperties.Ai.Cache config) {
        return new SemanticAnswerCache(config, vectors, (article, version) -> true, clock);
    }

    private ConsultationProperties.Ai.Cache cacheConfig() {
        ConsultationProperties.Ai.Cache config = new ConsultationProperties.Ai.Cache();
        config.setEnabled(true);
        config.setEmbeddingModel("ksp-embedding-v1");
        return config;
    }

    private RagQuery question(String text) {
        return new RagQuery("S1", text, List.of(), "C_NET", "ASSET1", 3, new RagCaller("U1", "EMPLOYEE"));
    }

    private RagQuery followUp(String text) {
        return new RagQuery("S1", text, List.of(new RagQuery.Turn("user", "刚才说的问题")),
                "C_NET", "ASSET1", 3, new RagCaller("U1", "EMPLOYEE"));
    }

    private static KnowledgeCitationDto citation(String version) {
        return new KnowledgeCitationDto("A1", version, "会议音频排障", new BigDecimal("0.85"), "检查输入设备。");
    }

    private static RagResult answered(String answer, String version) {
        return new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, answer, List.of(citation(version)),
                new BigDecimal("0.9100"), null, "local-rag-1.0", List.of(version), 100, null, false, false);
    }

    private static RagCallContext context() {
        return new RagCallContext("req-1", System.nanoTime() + 10_000_000_000L, new RagExecutionAudit());
    }

    @Test
    void validAnswerIsWrittenWithoutAnyCounters() {
        SemanticAnswerCache cache = cache(cacheConfig());
        cache.write(question("会议没有声音怎么处理"), context(), answered("检查输入设备。", "V1"));
        assertThat(cache.stats().entries()).isEqualTo(1);
        assertThat(cache.stats().hits()).isZero();
        assertThat(cache.stats().realMisses()).isZero();
        assertThat(cache.stats().depFailures()).isZero();
    }

    @Test
    void refusalsClarificationsGeneralAnswersAndDegradedResultsAreNeverWritten() {
        SemanticAnswerCache cache = cache(cacheConfig());
        cache.write(question("q"), context(), RagResult.refuse(AiRefusalReason.LOW_CONFIDENCE, "m", List.of("V1")));
        cache.write(question("q"), context(), new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY, "请说明设备。",
                List.of(citation("V1")), new BigDecimal("0.9100"), null, "m", List.of("V1"), 1, null, false, false));
        cache.write(question("q"), context(), new RagResult(RagStatus.SUCCESS, AiReplyType.ANSWER, "通用建议。",
                List.of(), new BigDecimal("0.9100"), null, "m", List.of(), 1, null, true, false));
        cache.write(question("q"), context(), RagResult.degraded(RagStatus.TIMEOUT, "TIMEOUT", 50));
        cache.write(question("q"), context(), RagResult.degraded(RagStatus.UNAVAILABLE, "UNAVAILABLE", 50));
        assertThat(cache.stats().entries()).isZero();
        assertThat(cache.stats().depFailures()).isZero();
    }

    @Test
    void followUpQuestionsAreNotWritten() {
        SemanticAnswerCache cache = cache(cacheConfig());
        cache.write(followUp("那上海呢"), context(), answered("答案。", "V1"));
        assertThat(cache.stats().entries()).isZero();
    }

    @Test
    void embeddingFailureIsCountedAsDependencyFailureAndSwallowed() {
        SemanticAnswerCache cache = new SemanticAnswerCache(cacheConfig(),
                (text, ctx) -> { throw DependencyFailure.invalid(); }, (a, v) -> true, clock);
        assertThatCode(() -> cache.write(question("q"), context(), answered("答案。", "V1"))).doesNotThrowAnyException();
        assertThat(cache.stats().entries()).isZero();
        assertThat(cache.stats().depFailures()).isEqualTo(1);
    }

    @Test
    void disabledInstanceIsPassThrough() {
        SemanticAnswerCache disabled = SemanticAnswerCache.disabled();
        assertThatCode(() -> disabled.write(question("q"), context(), answered("答案。", "V1"))).doesNotThrowAnyException();
        assertThatCode(disabled::stats).doesNotThrowAnyException();
        assertThat(disabled.lookup(question("q"), context())).isEmpty();
        assertThat(disabled.stats().entries()).isZero();
    }

    @Test
    void synonymousRewriteReplacesEntryInsteadOfAppending() {
        SemanticAnswerCache cache = cache(cacheConfig());
        cache.write(question("会议没有声音"), context(), answered("旧答案。", "V1"));
        nextVector.set(new float[]{0.99f, 0.02f});
        cache.write(question("开会别人听不到我"), context(), answered("新答案。", "V2"));
        assertThat(cache.stats().entries()).isEqualTo(1);
        Optional<CachedAnswer> hit = cache.lookup(question("开会别人听不到我"), context());
        assertThat(hit).isPresent();
        assertThat(hit.get().result().answerText()).isEqualTo("新答案。");
        assertThat(hit.get().result().retrievedVersionIds()).containsExactly("V2");
    }

    @Test
    void lruEvictsOldestEntryWhenFull() {
        ConsultationProperties.Ai.Cache config = cacheConfig();
        config.setMaxEntries(2);
        SemanticAnswerCache cache = cache(config);
        cache.write(question("q1"), context(), answered("a1", "V1"));
        nextVector.set(new float[]{0f, 1f});
        cache.write(question("q2"), context(), answered("a2", "V2"));
        nextVector.set(new float[]{0.7f, 0.7f});
        cache.write(question("q3"), context(), answered("a3", "V3"));
        assertThat(cache.stats().entries()).isEqualTo(2);
        assertThat(cache.stats().evictionsLru()).isEqualTo(1);
        nextVector.set(new float[]{1f, 0f});
        assertThat(cache.lookup(question("q1"), context())).isEmpty();
    }

    @Test
    void expiredEntriesAreLazilyEvictedOnWriteAndLookup() {
        ConsultationProperties.Ai.Cache config = cacheConfig();
        config.setTtlSeconds(3600);
        SemanticAnswerCache cache = cache(config);
        cache.write(question("q1"), context(), answered("a1", "V1"));
        clock.advanceSeconds(3601);
        assertThat(cache.lookup(question("q1"), context())).isEmpty();
        assertThat(cache.stats().evictionsTtl()).isEqualTo(1);
        assertThat(cache.stats().entries()).isZero();
    }

    @Test
    void writeWithinDebounceWindowDoesNotReplace() {
        ConsultationProperties.Ai.Cache config = cacheConfig();
        config.setMinWriteIntervalSeconds(60);
        SemanticAnswerCache cache = cache(config);
        cache.write(question("会议没有声音"), context(), answered("旧答案。", "V1"));
        cache.write(question("会议没声音"), context(), answered("新答案。", "V2"));
        Optional<CachedAnswer> hit = cache.lookup(question("会议没有声音"), context());
        assertThat(hit).isPresent();
        assertThat(hit.get().result().answerText()).isEqualTo("旧答案。");
    }
}
