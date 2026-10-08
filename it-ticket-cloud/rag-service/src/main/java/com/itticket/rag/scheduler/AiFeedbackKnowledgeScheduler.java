package com.itticket.rag.scheduler;

import com.itticket.rag.dto.AiFeedbackCandidate;
import com.itticket.rag.mapper.AiFeedbackSourceMapper;
import com.itticket.rag.service.AiFeedbackKnowledgeService;
import com.itticket.rag.service.AiFeedbackProcessingCache;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(prefix = "rag.ai-feedback", name = "enabled", havingValue = "true", matchIfMissing = true)
public class AiFeedbackKnowledgeScheduler {
    private final AiFeedbackSourceMapper source;
    private final AiFeedbackKnowledgeService service;
    private final AiFeedbackProcessingCache cache;
    private String afterId = "";

    @Scheduled(fixedDelayString = "${rag.ai-feedback.poll-delay-ms:5000}",
            initialDelayString = "${rag.ai-feedback.poll-delay-ms:5000}")
    public void consume() {
        List<AiFeedbackCandidate> candidates = source.findPending(afterId, 100);
        if (candidates.isEmpty()) {
            afterId = "";
            return;
        }
        for (AiFeedbackCandidate candidate : candidates) {
            try {
                if (!cache.wasProcessed(candidate.interactionId())) {
                    service.capture(candidate);
                    cache.markProcessed(candidate.interactionId());
                }
            } catch (RuntimeException e) {
                // 不缓存失败；下轮从头扫描补偿。确定性数据库主键也兜底跨实例竞争。
                log.error("AI feedback knowledge capture failed: interactionId={}", candidate.interactionId(), e);
            }
            // 包括不合规和失败记录，均推进本轮游标，避免毒消息阻塞后续反馈。
            afterId = candidate.interactionId();
        }
    }
}
