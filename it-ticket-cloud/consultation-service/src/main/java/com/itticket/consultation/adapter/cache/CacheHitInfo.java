package com.itticket.consultation.adapter.cache;

/**
 * 命中审计元数据:相似度与条目作用域(categoryId/assetId),Task 5 挂到
 * RagResult 内部组件 cacheHit,随 consultation_message.metadata 落库。
 */
public record CacheHitInfo(double similarity, String scope) {}
