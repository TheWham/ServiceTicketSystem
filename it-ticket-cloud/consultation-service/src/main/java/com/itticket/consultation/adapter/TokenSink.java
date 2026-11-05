package com.itticket.consultation.adapter;

import java.util.Objects;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

/**
 * 打字机出口闸门(T-4):answerText 增量 token 经 accept 外发一次即记 emitted。
 *
 * <p>职责边界:
 * <ul>
 *   <li>accept(token) 只做转发与外发标记,不做缓冲、不做速率整形——节流策略由下游(SSE 编排器)决定;</li>
 *   <li>emitted() 供编排侧做重试抑制与缓存命中单发判定:已外发过的流不再重试、不替换文本,
 *       避免向用户重复发送字符;</li>
 *   <li>空串/null 忽略不计数——拒答路径的空 answerText 不会假装"已外发"。</li>
 * </ul>
 */
public final class TokenSink implements Consumer<String> {

    private final Consumer<String> downstream;
    private final AtomicBoolean emitted = new AtomicBoolean();

    private TokenSink(Consumer<String> downstream) {
        this.downstream = downstream;
    }

    /** 包装一个真实下游(如 SSE token 事件发射器)。 */
    public static TokenSink of(Consumer<String> downstream) {
        return new TokenSink(Objects.requireNonNull(downstream));
    }

    /** 丢弃式出口:本地抽取式生成器等无增量可流的路径用,accept 不外发但仍记录 emitted。 */
    public static TokenSink discarding() {
        return new TokenSink(null);
    }

    @Override
    public void accept(String token) {
        if (token == null || token.isEmpty()) return;
        if (downstream != null) downstream.accept(token);
        emitted.set(true);
    }

    /** 是否已外发过至少一个 token(重试抑制/缓存单发判定)。 */
    public boolean emitted() {
        return emitted.get();
    }
}
