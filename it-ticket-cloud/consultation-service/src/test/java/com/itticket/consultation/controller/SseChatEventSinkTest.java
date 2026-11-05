package com.itticket.consultation.controller;

import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.support.Json;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SSE 桥(T-6)帧协议与断连行为测试。final/error 帧的载荷字面量就是前端
 * {@code aiMessageStream} 要解析的契约,这里逐字锁定,防止协议漂移。
 */
class SseChatEventSinkTest {

    /** 捕获帧的假 emitter;broken=true 模拟传输已断。 */
    static final class RecordingEmitter extends ResponseBodyEmitter {
        final List<String> frames = new ArrayList<>();
        boolean complete;
        boolean broken;

        @Override
        public synchronized void send(Object data, MediaType mediaType) throws IOException {
            if (broken) throw new IOException("客户端已断开");
            assertThat(mediaType).isEqualTo(MediaType.TEXT_EVENT_STREAM);
            frames.add(new String((byte[]) data, StandardCharsets.UTF_8));
        }

        @Override
        public synchronized void complete() {
            this.complete = true;
        }
    }

    private static AiChatResponse answer() {
        return new AiChatResponse("C-1", AiReplyType.ANSWER, "重启路由器。",
                null, null, false, null, "deepseek-v4-flash", "I-1");
    }

    @Test
    void framesForEveryEventMatchTheFrontendProtocolVerbatim() {
        RecordingEmitter emitter = new RecordingEmitter();
        SseChatEventSink sink = new SseChatEventSink(emitter);

        sink.comment("keep-alive");
        sink.queued(2);
        sink.token("重启");
        sink.token("路由");
        sink.completed(answer());

        assertThat(emitter.frames).containsExactly(
                ": keep-alive\n\n",
                "event: queued\ndata: {\"position\":2}\n\n",
                "event: token\ndata: {\"text\":\"重启\"}\n\n",
                "event: token\ndata: {\"text\":\"路由\"}\n\n",
                "event: final\ndata: " + Json.write(answer()) + "\n\n");
        assertThat(emitter.complete).isTrue();
        assertThat(sink.isOpen()).isFalse();
    }

    @Test
    void failedEmitsErrorEventWithRealErrorClassAndCompletesChannel() {
        RecordingEmitter emitter = new RecordingEmitter();
        SseChatEventSink sink = new SseChatEventSink(emitter);

        sink.failed("TIMEOUT", "排队等待超出请求预算");

        assertThat(emitter.frames).containsExactly(
                "event: error\ndata: {\"errorClass\":\"TIMEOUT\",\"message\":\"排队等待超出请求预算\"}\n\n");
        assertThat(emitter.complete).isTrue();
        assertThat(sink.isOpen()).isFalse();

        // error 之后通道关闭:后续任何事件都被丢弃,不再显式补发。
        sink.token("迟到的令牌");
        assertThat(emitter.frames).hasSize(1);
    }

    @Test
    void transportFailureClosesSinkAndFurtherEventsAreDroppedQuietly() {
        RecordingEmitter emitter = new RecordingEmitter();
        SseChatEventSink sink = new SseChatEventSink(emitter);
        emitter.broken = true;

        sink.token("重启"); // 写帧遇 IOException:标记断连,不向上抛

        assertThat(sink.isOpen()).isFalse();
        sink.queued(1);
        sink.completed(answer());
        sink.failed("TIMEOUT", "后续");
        assertThat(emitter.frames).isEmpty();
        assertThat(emitter.complete).isTrue(); // completeQuietly 容器拒绝也不视作故障
    }
}
