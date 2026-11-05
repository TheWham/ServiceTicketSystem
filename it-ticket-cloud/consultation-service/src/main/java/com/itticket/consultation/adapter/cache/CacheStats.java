package com.itticket.consultation.adapter.cache;

import java.util.List;

/**
 * 只读运行快照。三态计数严格区分:
 * hits=命中出缓存(哨兵复核通过);realMisses=真实未命中(含 TTL/哨兵驱逐后的穿透);
 * depFailures=依赖失败(嵌入端点故障、哨兵 SQL 异常)。hitRate=hits/(hits+realMisses),
 * 分母为 0 取 0;recentSimilarities=最近 50 次命中的相似度(审计阈值调参用)。
 */
public record CacheStats(long hits, long realMisses, long depFailures,
                         long evictionsTtl, long evictionsLru, long evictionsSentinel,
                         long entries, double hitRate, double maxHitSimilarity,
                         List<Double> recentSimilarities) {

    static CacheStats empty() {
        return new CacheStats(0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, List.of());
    }
}
