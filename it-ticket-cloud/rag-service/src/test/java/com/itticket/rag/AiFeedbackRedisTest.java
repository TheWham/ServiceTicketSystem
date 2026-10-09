package com.itticket.rag;

import com.itticket.rag.service.AiFeedbackProcessingCache;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.util.UUID;
import java.time.Duration;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** 使用随机测试 ID，不读写真实业务缓存；可指定实际 Redis 地址及认证。 */
@EnabledIfEnvironmentVariable(named = "AI_FEEDBACK_REDIS_TEST", matches = "true")
class AiFeedbackRedisTest {
    @Test void realRedisCachesFeedbackWithTtlAndEnvironmentIsolation() {
        var config = new RedisStandaloneConfiguration(
                System.getenv().getOrDefault("REDIS_HOST", "127.0.0.1"),
                Integer.parseInt(System.getenv().getOrDefault("REDIS_PORT", "6379")));
        config.setDatabase(Integer.parseInt(System.getenv().getOrDefault("REDIS_DATABASE", "0")));
        String password = System.getenv("REDIS_PASSWORD");
        if (password != null && !password.isBlank()) config.setPassword(password);
        var factory = new LettuceConnectionFactory(config);
        factory.afterPropertiesSet();
        factory.start();
        var redis = new StringRedisTemplate(factory);
        String id = "probe-" + UUID.randomUUID();
        String key = "its:test:cache:ai-feedback:" + id;
        try {
            var cache = new AiFeedbackProcessingCache(redis, "test", 300);
            var isolated = new AiFeedbackProcessingCache(redis, "other-test", 300);
            assertThat(cache.wasProcessed(id)).isFalse();
            cache.markProcessed(id);
            assertThat(redis.opsForValue().get(key)).isEqualTo("processed");
            assertThat(cache.wasProcessed(id)).isTrue();
            assertThat(redis.getExpire(key, TimeUnit.SECONDS)).isBetween(1L, 300L);
            assertThat(isolated.wasProcessed(id)).isFalse();
            redis.expire(key, Duration.ofMillis(150));
            await().atMost(Duration.ofSeconds(3)).untilAsserted(() -> assertThat(cache.wasProcessed(id)).isFalse());
        } finally {
            redis.delete(key);
            factory.destroy();
        }
    }
}
