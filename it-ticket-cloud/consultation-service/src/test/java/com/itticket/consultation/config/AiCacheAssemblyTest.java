package com.itticket.consultation.config;

import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagCaller;
import com.itticket.consultation.adapter.cache.SemanticAnswerCache;
import com.itticket.consultation.service.KnowledgeQueryService;
import org.junit.jupiter.api.Test;


import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;

/**
 * 装配期构建语义缓存的 fail-fast 语义(AC-004: 装配期而非运行时再失败)。
 * 默认关闭必须零依赖(disabled 实例),开启则对嵌入模型/阈值/基址做启动期校验。
 */
class AiCacheAssemblyTest {

    private static ConsultationProperties properties() {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setBaseUrl("http://127.0.0.1:9000");
        properties.getAi().setApiKey("key");
        return properties;
    }

    private static RagQuery firstTurnQuery() {
        return new RagQuery("S1", "VPN 断连", "C_NET", "ASSET1", 5, new RagCaller("U1", "EMPLOYEE"));
    }

    private static RagCallContext context() {
        return new RagCallContext("req-asm", System.nanoTime() + 10_000_000_000L, new RagExecutionAudit());
    }

    @Test
    void disabledByDefaultYieldsInertCacheWithoutEmbeddingModel() {
        ConsultationProperties properties = properties(); // enabled=false 且 embeddingModel 为空也不该抛
        AiCompositionConfig config = new AiCompositionConfig();
        SemanticAnswerCache cache = config.semanticAnswerCache(
                properties, new DependencyHttpClient(), mock(KnowledgeQueryService.class));

        assertThat(cache.lookup(firstTurnQuery(), context())).isEmpty();
        cache.write(firstTurnQuery(), context(), null); // 写入侧同样直通,不抛
        assertThat(cache.stats().entries()).isZero();
    }

    @Test
    void enabledWithoutEmbeddingModelFailsFastWithConfigKeyInMessage() {
        ConsultationProperties properties = properties();
        properties.getAi().getCache().setEnabled(true);

        AiCompositionConfig config = new AiCompositionConfig();
        assertThatThrownBy(() -> config.semanticAnswerCache(
                properties, new DependencyHttpClient(), mock(KnowledgeQueryService.class)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("itticket.consultation.ai.cache.embedding-model");
    }

    @Test
    void enabledWithUnderminedThresholdFailsFast() {
        ConsultationProperties properties = properties();
        properties.getAi().getCache().setEnabled(true);
        properties.getAi().getCache().setEmbeddingModel("bge-m3");
        properties.getAi().getCache().setThreshold(0.5);

        AiCompositionConfig config = new AiCompositionConfig();
        assertThatThrownBy(() -> config.semanticAnswerCache(
                properties, new DependencyHttpClient(), mock(KnowledgeQueryService.class)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("itticket.consultation.ai.cache.threshold");
    }

    @Test
    void enabledBuildsWorkingCacheWithBaseUrlFallback() {
        ConsultationProperties properties = properties(); // embeddingBaseUrl 留空 → 回退 ai.baseUrl
        properties.getAi().getCache().setEnabled(true);
        properties.getAi().getCache().setEmbeddingModel("bge-m3");

        AiCompositionConfig config = new AiCompositionConfig();
        SemanticAnswerCache cache = config.semanticAnswerCache(
                properties, new DependencyHttpClient(), mock(KnowledgeQueryService.class));

        assertThat(cache.stats().entries()).isZero();
    }

    @Test
    void enabledWithoutAnyBaseUrlFailsFast() {
        ConsultationProperties properties = properties();
        properties.getAi().setBaseUrl("");
        properties.getAi().setApiKey("key");
        properties.getAi().getCache().setEnabled(true);
        properties.getAi().getCache().setEmbeddingModel("bge-m3");

        AiCompositionConfig config = new AiCompositionConfig();
        assertThatThrownBy(() -> config.semanticAnswerCache(
                properties, new DependencyHttpClient(), mock(KnowledgeQueryService.class)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("embedding-base-url");
    }

    @Test
    void enabledWithNonPositiveTtlFailsFast() {
        ConsultationProperties properties = properties();
        properties.getAi().getCache().setEnabled(true);
        properties.getAi().getCache().setEmbeddingModel("bge-m3");
        properties.getAi().getCache().setTtlSeconds(0);

        AiCompositionConfig config = new AiCompositionConfig();
        assertThatThrownBy(() -> config.semanticAnswerCache(
                properties, new DependencyHttpClient(), mock(KnowledgeQueryService.class)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("itticket.consultation.ai.cache.ttl-seconds");
    }
}
