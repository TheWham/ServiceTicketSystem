package com.itticket.rag;

import com.itticket.rag.dto.AiFeedbackCandidate;
import com.itticket.rag.mapper.AiFeedbackSourceMapper;
import com.itticket.rag.scheduler.AiFeedbackKnowledgeScheduler;
import com.itticket.rag.service.AiFeedbackKnowledgeService;
import com.itticket.rag.service.AiFeedbackProcessingCache;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import java.time.Duration;
import java.util.List;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class AiFeedbackSchedulerTest {
    final AiFeedbackSourceMapper source = mock(AiFeedbackSourceMapper.class);
    final AiFeedbackKnowledgeService service = mock(AiFeedbackKnowledgeService.class);
    final StringRedisTemplate redis = mock(StringRedisTemplate.class);
    @SuppressWarnings("unchecked")
    final ValueOperations<String, String> values = mock(ValueOperations.class);
    final AiFeedbackProcessingCache cache = new AiFeedbackProcessingCache(redis, "test", 300);
    final AiFeedbackKnowledgeScheduler scheduler = new AiFeedbackKnowledgeScheduler(source, service, cache);
    final AiFeedbackCandidate first = new AiFeedbackCandidate("A1", "S1", "U1", "C_NET", "question", "answer");
    final AiFeedbackCandidate second = new AiFeedbackCandidate("A2", "S1", "U1", "C_NET", "question2", "answer2");

    AiFeedbackSchedulerTest() { when(redis.opsForValue()).thenReturn(values); }

    @Test void cachesOnlyAfterSuccessfulTransactionAndSkipsCachedSource() {
        when(source.findPending("", 100)).thenReturn(List.of(first, second));
        when(values.get("its:test:cache:ai-feedback:A1")).thenReturn("processed");
        scheduler.consume();
        verify(service, never()).capture(first);
        var order = inOrder(service, values);
        order.verify(service).capture(second);
        order.verify(values).set("its:test:cache:ai-feedback:A2", "processed", Duration.ofSeconds(300));
    }

    @Test void databaseFailureDoesNotCacheSuccessOrBlockLaterFeedbackAndIsRetried() {
        when(source.findPending("", 100)).thenReturn(List.of(first, second));
        when(source.findPending("A2", 100)).thenReturn(List.of());
        when(service.capture(first)).thenThrow(new IllegalStateException("database unavailable"));
        scheduler.consume();
        verify(values, never()).set(eq("its:test:cache:ai-feedback:A1"), anyString(), any(Duration.class));
        verify(service).capture(second);
        scheduler.consume(); // 到达尾部后重置游标
        scheduler.consume();
        verify(service, times(2)).capture(first);
    }

    @Test void redisUnavailableFallsBackToDatabase() {
        when(source.findPending("", 100)).thenReturn(List.of(first));
        when(redis.opsForValue()).thenThrow(new IllegalStateException("redis unavailable"));
        scheduler.consume();
        verify(service).capture(first);
    }
}
