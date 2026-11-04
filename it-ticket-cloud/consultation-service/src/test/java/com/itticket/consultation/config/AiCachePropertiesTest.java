package com.itticket.consultation.config;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 语义答案缓存配置项(itticket.consultation.ai.cache.*)的默认值契约:
 *  - 默认关闭(enabled=false),关闭时全系统行为与引入缓存前完全一致;
 *  - 相似度阈值 0.93(讲义教学值 0.92 的更保守取值,低于 0.90 装配期拒绝);
 *  - 容量 500 条、TTL 7 天(与知识版本哨兵的时效兜底一致);
 *  - 嵌入端点默认回退 ai.base-url,嵌入模型必填由装配期 fail-fast 校验。
 */
class AiCachePropertiesTest {

    @Test
    void cacheDefaultsAreSafe() {
        ConsultationProperties.Ai.Cache cache = new ConsultationProperties().getAi().getCache();

        assertThat(cache.isEnabled()).isFalse();
        assertThat(cache.getThreshold()).isEqualTo(0.93);
        assertThat(cache.getMaxEntries()).isEqualTo(500);
        assertThat(cache.getTtlSeconds()).isEqualTo(604800L);
        assertThat(cache.getEmbeddingModel()).isNull();
        assertThat(cache.getEmbeddingBaseUrl()).isNull();
        assertThat(cache.getEmbeddingTimeoutMs()).isEqualTo(1000L);
        assertThat(cache.getMinWriteIntervalSeconds()).isEqualTo(0L);
    }
}
