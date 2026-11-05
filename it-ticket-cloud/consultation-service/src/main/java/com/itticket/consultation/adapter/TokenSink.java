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
 *   <li>空串/null 忽略不计数——拒答路径的空 answerText 不会假装“已外发”;</li>
 *   <li>可子类化:编排器用它挂载断连标记({@link #clientGone()})与首字节哨兵
 *       ({@link #armFirstTokenGuard()});无哨兵语义的调用方不受影响。</li>
 * </ul>
 */
public class TokenSink implements Consumer<String> {

    private final Consumer<String> downstream;
    private final AtomicBoolean emitted = new AtomicBoolean();

    protected TokenSink(Consumer<String> downstream) {
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

    /**
     * 客户端是否已断连/中止本流。持久化门槛(服务层落库前)与令牌出口据此在中止后不再续流续写——
     * 默认恒 false(非流式/丢弃型出口无断连概念),编排器的流式出口覆盖它。
     */
    public boolean clientGone() {
        return false;
    }

    /**
     * 首字节哨兵布设钩子:仅「本地生成路径」在外发前调用;缓存命中(先于生成)与
     * agent 路径(Python 侧无流)不调用,因此天然豁免首字节超时裁决①。
     * 默认空实现——非编排器装配的出口无哨兵可布。
     */
    public void armFirstTokenGuard() {
    }
}
