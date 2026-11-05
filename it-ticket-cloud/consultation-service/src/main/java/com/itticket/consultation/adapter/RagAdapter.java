package com.itticket.consultation.adapter;

/**
 * RAG 编排适配器。tokenSink 用于流式链路增量外发 answerText(非流式调用方传
 * {@link TokenSink#discarding()}),拒答/澄清/降级路径不调 sink。
 */
public interface RagAdapter {
    RagResult answer(RagQuery query, RagCallContext context, TokenSink tokenSink);
}
