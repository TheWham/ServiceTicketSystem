package com.itticket.consultation.config;

import com.itticket.consultation.adapter.TokenSink;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.service.AiConsultationService;
import com.itticket.consultation.service.CurrentUser;
import com.itticket.consultation.service.stream.AiChatStreamOrchestrator;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * streaming.enabled 的装配语义(T-6,裁决②):端点常在,开关只决定
 * 生成期间增量令牌是否上屏;false=引擎收到丢弃型 sink,口径与旧同步端点一致,
 * 前端看到的仍是"整段单 token + final",无需调用侧兜底。
 *
 * <p>分支只存在于本装配类(AiStreamConfig);编排器与引擎均对开关无感知。
 */
class AiStreamConfigTest {

    private static CurrentUser employee() {
        return new CurrentUser("U_EMP01", com.itticket.consultation.enums.RoleCode.EMPLOYEE, null);
    }

    /** 记录事件的假 SSE 出口:"token:x"=生成期间外发的增量(或整段重放)。 */
    static final class RecordingSink implements AiChatStreamOrchestrator.EventSink {
        final List<String> events = new CopyOnWriteArrayList<>();
        volatile boolean open = true;

        @Override public void comment(String text) { }
        @Override public void queued(int position) { events.add("queued:" + position); }
        @Override public void token(String text) { events.add("token:" + text); }
        @Override public void completed(AiChatResponse response) { events.add("final"); open = false; }
        @Override public void failed(String errorClass, String message) { events.add("error:" + errorClass); open = false; }
        @Override public boolean isOpen() { return open; }
    }

    private static AiChatResponse answer(String text) {
        return new AiChatResponse("C-1", AiReplyType.ANSWER, text, null, null, false, null,
                "deepseek-v4-flash", "I-1");
    }

    private static AiConsultationService engine(AtomicReference<TokenSink> captured) {
        AiConsultationService service = mock(AiConsultationService.class);
        when(service.chatStreamed(any(), any(), any(), any(), any(), anyLong())).thenAnswer(invocation -> {
            TokenSink sink = invocation.getArgument(4);
            captured.set(sink);
            sink.accept("增量");
            return answer("完整答案");
        });
        return service;
    }

    private record Wired(RecordingSink sink, AtomicReference<TokenSink> captured) { }

    private Wired runOnce(boolean streamingEnabled) throws InterruptedException {
        AtomicReference<TokenSink> captured = new AtomicReference<>();
        AiConsultationService engine = engine(captured);
        AiChatStreamOrchestrator orchestrator =
                new AiStreamConfig().aiChatStreamOrchestrator(properties(streamingEnabled), engine);
        try {
            RecordingSink sink = new RecordingSink();
            orchestrator.openStream(employee(), "C-1",
                    new AiChatRequest("投影仪没有信号", null), "key-1", sink);
            awaitFinal(sink);
            ArgumentCaptor<TokenSink> engineSink = ArgumentCaptor.forClass(TokenSink.class);
            verify(engine).chatStreamed(any(), any(), any(), any(), engineSink.capture(), anyLong());
            return new Wired(sink, new AtomicReference<>(engineSink.getValue()));
        } finally {
            orchestrator.close();
        }
    }

    private static void awaitFinal(RecordingSink sink) throws InterruptedException {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (!sink.events.contains("final")) {
            if (System.nanoTime() > deadline) {
                throw new AssertionError("5 秒内未收到 final,实际事件: " + sink.events);
            }
            TimeUnit.MILLISECONDS.sleep(20);
        }
    }

    private ConsultationProperties properties(boolean streamingEnabled) {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().getStreaming().setEnabled(streamingEnabled);
        return properties;
    }

    @Test
    void enabledStreamsTypewriterTokensThroughTheOrchestratorSink() throws InterruptedException {
        Wired run = runOnce(true);

        // 直通:引擎收到的是编排器的 StreamSink(非基类 TokenSink 实例),增量原样上屏;
        // 引擎已外发,编排器不再重放整段。
        assertThat(run.captured.get().getClass()).isNotEqualTo(TokenSink.class);
        assertThat(run.captured.get().emitted()).isTrue();
        assertThat(run.sink.events).contains("token:增量");
        assertThat(run.sink.events).doesNotContain("token:完整答案");
        assertThat(run.sink.events).endsWith("final");
    }

    @Test
    void disabledKeepsLegacySingleTokenContractUsingADiscardingSink() throws InterruptedException {
        Wired run = runOnce(false);

        // 屏蔽:引擎收到丢弃型 TokenSink(基类实例),生成期间零外发;
        // 编排器据此整段重放一次,口径与旧同步端点一致。
        assertThat(run.captured.get().getClass()).isEqualTo(TokenSink.class);
        assertThat(run.sink.events).doesNotContain("token:增量");
        assertThat(run.sink.events).containsExactly("token:完整答案", "final");
    }
}
