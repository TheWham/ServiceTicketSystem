package com.itticket.consultation.adapter.embedding;

import com.itticket.consultation.adapter.RagCallContext;

/**
 * 问题嵌入端口:语义答案缓存与检索侧共用的向量来源。
 * 实现必须返回 L2 归一化的向量(余弦相似度匹配的前提),并把调用计入
 * {@link RagCallContext} 的统一超时预算。失败一律抛 {@link com.itticket.consultation.adapter.DependencyFailure},
 * 不静默回退:嵌入不可用意味着缓存既不能读也不能写,由上层按依赖失败计数。
 */
public interface EmbeddingClient {

    /** 返回给定文本的归一化 embedding;协议违规或依赖故障抛 DependencyFailure。 */
    float[] embed(String text, RagCallContext context);
}
