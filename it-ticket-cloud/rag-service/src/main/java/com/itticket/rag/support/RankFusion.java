package com.itticket.rag.support;

import com.itticket.rag.vo.ChunkHit;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * ============================================================================
 * 检索结果排序融合 (RankFusion)
 * ============================================================================
 *
 * 【设计意图】：
 * 向量检索（kNN，余弦）与全文检索（BM25）各自的打分体系不可直接比较，
 * 因此采用 Reciprocal Rank Fusion（RRF）按名次融合，避免分数归一化带来的调参负担：
 *
 *     rrf(d) = Σ_list 1 / (K + rank_list(d))，本实现 K = 60（业界常用值）
 *
 * 余弦相似度独立保留在 {@link ChunkHit#cosineSimilarity()} 上，不参与融合打分，
 * 以确保阈值判定（如 0.65）始终基于真实语义相似度。
 *
 * @author IT工单系统研发组 - RAG专项
 */
public final class RankFusion {

    /** RRF 平滑常数 */
    public static final int RRF_K = 60;

    private RankFusion() {
    }

    /**
     * 融合向量路与全文路命中，按 RRF 分值降序返回 Top-K。
     *
     * @param knnHits  向量检索命中（须按相似度降序）
     * @param textHits 全文检索命中（须按 BM25 降序）
     * @param topK     返回条数上限
     */
    public static List<ChunkHit> fuse(List<ChunkHit> knnHits, List<ChunkHit> textHits, int topK) {
        Map<String, Fused> merged = new LinkedHashMap<>();

        int rank = 0;
        for (ChunkHit hit : nullSafe(knnHits)) {
            rank++;
            Fused fused = merged.computeIfAbsent(hit.chunkId(), id -> new Fused(hit));
            fused.hit = hit;
            fused.knnRank = rank;
            fused.rrf += 1d / (RRF_K + rank);
        }

        rank = 0;
        for (ChunkHit hit : nullSafe(textHits)) {
            rank++;
            Fused fused = merged.computeIfAbsent(hit.chunkId(), id -> new Fused(hit));
            fused.textRank = rank;
            fused.rrf += 1d / (RRF_K + rank);
        }

        List<Fused> ordered = new ArrayList<>(merged.values());
        ordered.sort((a, b) -> Double.compare(b.rrf, a.rrf));

        List<ChunkHit> result = new ArrayList<>(Math.min(topK, ordered.size()));
        for (Fused fused : ordered) {
            if (result.size() >= topK) {
                break;
            }
            ChunkHit h = fused.hit;
            result.add(new ChunkHit(h.chunkId(), h.articleId(), h.versionId(), h.title(), h.content(),
                    h.categoryId(), h.cosineSimilarity(), fused.knnRank, fused.textRank, fused.rrf));
        }
        return result;
    }

    private static List<ChunkHit> nullSafe(List<ChunkHit> hits) {
        return hits == null ? List.of() : hits;
    }

    /** 融合过程中的可变累积项 */
    private static final class Fused {
        private ChunkHit hit;
        private int knnRank = -1;
        private int textRank = -1;
        private double rrf;

        private Fused(ChunkHit hit) {
            this.hit = hit;
        }
    }
}
