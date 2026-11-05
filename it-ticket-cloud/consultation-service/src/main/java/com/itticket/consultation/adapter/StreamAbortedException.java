package com.itticket.consultation.adapter;

/**
 * 流式回答被客户端断连终止时,由编排器的流式出口抛出并沿引擎调用链上抛,
 * 用于在持久化门槛之前中止本次会话回答的落库(与旧端点同律:AI 侧不半落)。
 *
 * <p>不用于外部协议——SSE 断连本身就是传输层事实,不会多带一个错误事件。
 */
public class StreamAbortedException extends RuntimeException {

    public StreamAbortedException(String message) {
        super(message);
    }
}
