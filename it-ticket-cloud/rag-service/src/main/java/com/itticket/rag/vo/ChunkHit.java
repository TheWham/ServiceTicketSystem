package com.itticket.rag.vo;

import java.math.BigDecimal;

/**
 * ============================================================================
 * 知识切片检索命中 (ChunkHit)
 * ============================================================================
 *
 * <p>携带向量/全文两路的命中信息，供 RRF 融合、置信度判定与知识引用组装使用。</p>
 *
 * @param cosineSimilarity 向量余弦相似度 [0,1]；仅向量路命中时有值，纯全文命中为 null
 * @param knnRank          向量路名次（1 起）；未命中为 -1
 * @param textRank         全文路名次（1 起）；未命中为 -1
 * @param rrfScore         RRF 融合分值，越大越靠前
 * @author IT工单系统研发组 - RAG专项
 */
public record ChunkHit(
        String chunkId,
        String articleId,
        String versionId,
        String title,
        String content,
        String categoryId,
        BigDecimal cosineSimilarity,
        int knnRank,
        int textRank,
        double rrfScore) {

    /** 构造原始命中（名次与融合分值待 RankFusion 填充） */
    public static ChunkHit raw(String chunkId, String articleId, String versionId, String title,
                               String content, String categoryId, BigDecimal cosineSimilarity) {
        return new ChunkHit(chunkId, articleId, versionId, title, content, categoryId,
                cosineSimilarity, -1, -1, 0d);
    }
}
