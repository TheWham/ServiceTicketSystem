package com.itticket.consultation.controller;

import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.service.stream.AiChatStreamOrchestrator;
import com.itticket.consultation.support.Json;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * SSE 桥(T-6):把编排器的流式事件翻译成 {@code text/event-stream} 帧写到
 * {@link ResponseBodyEmitter}。
 *
 * <p>帧协议(前端 {@code aiMessageStream} 对应解析):
 * <pre>
 * : keep-alive 空转注释行(排队与生成期间,兼作断连探测)
 * event: queued
 * data: {"position":1}
 *
 * event: token
 * data: {"text":"…增量答案…"}
 *
 * event: final
 * data: {…与旧 POST 端点相同的 AiChatResponse…}
 *
 * event: error
 * data: {"errorClass":"TIMEOUT","message":"…真实原因…"}
 * </pre>
 *
 * <p>final/error 之后通道视为关闭(isOpen=false),编排器据此掐掉空转帧;
 * 任一帧写出抛 {@link IOException} 同样视为客户端断连,后续事件静默丢弃,
 * 由编排器的断连中止逻辑中断上游。
 */
@Slf4j
public final class SseChatEventSink implements AiChatStreamOrchestrator.EventSink {

    private final ResponseBodyEmitter emitter;
    /** final/error 已发或传输已断即关;keep-alive 以此判断还有没有必要写。 */
    private volatile boolean open = true;

    public SseChatEventSink(ResponseBodyEmitter emitter) {
        this.emitter = emitter;
    }

    @Override public void comment(String text) {
        // SSE 注释行:冒号开头,客户端浏览器原生 EventSource 忽略,前端手解也不外显。
        frame(": " + text + "\n\n");
    }

    @Override public void queued(int position) {
        event("queued", "{\"position\":" + position + "}");
    }

    @Override public void token(String text) {
        event("token", "{\"text\":" + Json.write(text) + "}");
    }

    @Override public void completed(AiChatResponse response) {
        try {
            event("final", Json.write(response));
        } finally {
            open = false;
            completeQuietly();
        }
    }

    @Override public void failed(String errorClass, String message) {
        try {
            event("error", "{\"errorClass\":" + Json.write(String.valueOf(errorClass))
                    + ",\"message\":" + Json.write(message == null ? "" : message) + "}");
        } finally {
            open = false;
            completeQuietly();
        }
    }

    @Override public boolean isOpen() {
        return open;
    }

    private void event(String name, String data) {
        frame("event: " + name + "\ndata: " + data + "\n\n");
    }

    private void frame(String frame) {
        if (!open) return;
        try {
            emitter.send(frame.getBytes(StandardCharsets.UTF_8), MediaType.TEXT_EVENT_STREAM);
        } catch (IOException | IllegalStateException dead) {
            // 传输已断:标记断连,编排器在下一个令牌/保活出口中止本流。
            open = false;
            log.info("[ai-stream] SSE 出口已断开,本流进入断连中止: {}", dead.getMessage());
        }
    }

    private void completeQuietly() {
        try {
            emitter.complete();
        } catch (IllegalStateException ignored) {
            // 传输早已断开时容器会拒绝 complete,不是失败信号。
        }
    }
}
