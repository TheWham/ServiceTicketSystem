package com.itticket.consultation.config;

import com.itticket.consultation.adapter.TokenSink;
import com.itticket.consultation.service.AiConsultationService;
import com.itticket.consultation.service.stream.AiChatStreamOrchestrator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 流式回答装配(T-6)。编排器常驻,根因是 /stream 端点常在——
 * {@code itticket.consultation.ai.streaming.enabled} 只决定生成期间增量令牌
 * 是否上屏(打字机);false 时引擎收到丢弃型 sink,口径与旧同步端点完全一致,
 * 前端单一路径无需调用侧兜底(裁决②)。
 *
 * <p>首字节哨兵只读 {@code first-token-timeout-ms};排队预算复用
 * {@code request-timeout-ms}(统一超时预算,派发时间计入)。
 */
@Configuration(proxyBeanMethods = false)
public class AiStreamConfig {

    @Bean
    public AiChatStreamOrchestrator aiChatStreamOrchestrator(ConsultationProperties properties,
                                                             AiConsultationService aiConsultationService) {
        ConsultationProperties.Ai ai = properties.getAi();
        AiChatStreamOrchestrator.ChunkedChat engine = ai.getStreaming().isEnabled()
                ? aiConsultationService::chatStreamed
                : (user, sessionId, request, idempotencyKey, sink) ->
                        aiConsultationService.chatStreamed(user, sessionId, request, idempotencyKey,
                                TokenSink.discarding());
        return new AiChatStreamOrchestrator(engine,
                ai.getRequestTimeoutMs(),
                ai.getFirstTokenTimeoutMs(),
                ai.getStreaming().getKeepAliveMillis());
    }
}
