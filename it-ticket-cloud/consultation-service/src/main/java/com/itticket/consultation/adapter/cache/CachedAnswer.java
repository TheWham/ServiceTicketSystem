package com.itticket.consultation.adapter.cache;

import com.itticket.consultation.adapter.RagResult;

/**
 * 缓存命中的载荷:答案(不可变 RagResult,自带 citations 与 retrievedVersionIds
 * ——哨兵复核的失效锚点)加上命中相似度(审计用,不参与业务判定)。
 */
public record CachedAnswer(RagResult result, double similarity) {}
