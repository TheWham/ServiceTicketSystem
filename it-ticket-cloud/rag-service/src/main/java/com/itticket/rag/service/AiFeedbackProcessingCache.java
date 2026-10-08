package com.itticket.rag.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

/** Redis 仅缓存已检查来源的标记，不保存原始对话；MySQL 是持久化事实来源。 */
@Slf4j
@Component
public class AiFeedbackProcessingCache {
    private final StringRedisTemplate redis;
    private final String prefix;
    private final Duration ttl;
    private volatile long retryAfterNanos;

    public AiFeedbackProcessingCache(StringRedisTemplate redis,
            @Value("${rag.ai-feedback.cache-environment}") String environment,
            @Value("${rag.ai-feedback.cache-ttl-seconds:300}") long ttlSeconds) {
        if (environment == null || environment.isBlank() || ttlSeconds <= 0) {
            throw new IllegalArgumentException("AI feedback cache requires an environment and a positive TTL");
        }
        this.redis = redis;
        this.prefix = "its:" + environment + ":cache:ai-feedback:";
        this.ttl = Duration.ofSeconds(ttlSeconds);
    }

    public boolean wasProcessed(String interactionId) {
        if (unavailable()) return false;
        try {
            return "processed".equals(redis.opsForValue().get(prefix + interactionId));
        } catch (RuntimeException e) {
            degrade(e);
            return false;
        }
    }

    /** 必须在 capture 的 Spring 事务代理返回后调用，写库失败绝不缓存成功。 */
    public void markProcessed(String interactionId) {
        if (unavailable()) return;
        try {
            redis.opsForValue().set(prefix + interactionId, "processed", ttl);
        } catch (RuntimeException e) {
            degrade(e);
        }
    }

    private boolean unavailable() {
        return retryAfterNanos != 0 && System.nanoTime() - retryAfterNanos < 0;
    }

    private void degrade(RuntimeException e) {
        retryAfterNanos = System.nanoTime() + Duration.ofSeconds(30).toNanos();
        log.warn("AI feedback Redis cache unavailable; using MySQL for 30 seconds ({})", e.getClass().getSimpleName());
    }
}
