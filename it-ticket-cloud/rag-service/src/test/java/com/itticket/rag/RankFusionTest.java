package com.itticket.rag;

import com.itticket.rag.support.RankFusion;
import com.itticket.rag.vo.ChunkHit;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

/**
 * RRF 融合排序的单元测试。
 */
public class RankFusionTest {

    private static final BigDecimal COS_HIGH = new BigDecimal("0.9000");
    private static final BigDecimal COS_MID = new BigDecimal("0.7000");

    @Test
    public void chunkPresentInBothListsRanksFirst() {
        ChunkHit both = ChunkHit.raw("c1", "a1", "v1", "v1", "标题1", "内容1", "C_NET", COS_MID);
        ChunkHit knnOnly = ChunkHit.raw("c2", "a1", "v1", "v1", "标题2", "内容2", "C_NET", COS_HIGH);
        ChunkHit textOnly = ChunkHit.raw("c3", "a2", "v2", "v2", "标题3", "内容3", "C_NET", null);

        List<ChunkHit> fused = RankFusion.fuse(List.of(knnOnly, both), List.of(textOnly, both), 10);

        Assertions.assertEquals(3, fused.size());
        Assertions.assertEquals("c1", fused.get(0).chunkId(), "同时命中两路的切片应排在最前");
        Assertions.assertTrue(fused.get(0).rrfScore() > fused.get(1).rrfScore());
        Assertions.assertEquals(2, fused.get(0).knnRank());
        Assertions.assertEquals(2, fused.get(0).textRank());
    }

    @Test
    public void topKLimitsResultSize() {
        List<ChunkHit> knn = List.of(
                ChunkHit.raw("c1", "a1", "v1", "v1", "t", "x", "C_NET", COS_HIGH),
                ChunkHit.raw("c2", "a1", "v1", "v1", "t", "y", "C_NET", COS_MID),
                ChunkHit.raw("c3", "a2", "v2", "v2", "t", "z", "C_NET", COS_MID));

        List<ChunkHit> fused = RankFusion.fuse(knn, List.of(), 2);

        Assertions.assertEquals(2, fused.size());
        Assertions.assertEquals("c1", fused.get(0).chunkId());
    }

    @Test
    public void cosineSimilarityIsCarriedThroughUnchanged() {
        ChunkHit hit = ChunkHit.raw("c1", "a1", "v1", "v1", "t", "x", "C_NET", COS_HIGH);

        List<ChunkHit> fused = RankFusion.fuse(List.of(hit), List.of(), 5);

        Assertions.assertEquals(COS_HIGH, fused.get(0).cosineSimilarity(), "融合不得改写相似度");
    }

    @Test
    public void textOnlyHitKeepsNullCosine() {
        ChunkHit textOnly = ChunkHit.raw("c1", "a1", "v1", "v1", "t", "x", "C_NET", null);

        List<ChunkHit> fused = RankFusion.fuse(List.of(), List.of(textOnly), 5);

        Assertions.assertNull(fused.get(0).cosineSimilarity());
        Assertions.assertEquals(1, fused.get(0).textRank());
        Assertions.assertEquals(-1, fused.get(0).knnRank());
    }

    @Test
    public void emptyInputsReturnEmptyResult() {
        Assertions.assertTrue(RankFusion.fuse(List.of(), List.of(), 5).isEmpty());
        Assertions.assertTrue(RankFusion.fuse(null, null, 5).isEmpty());
    }
}
