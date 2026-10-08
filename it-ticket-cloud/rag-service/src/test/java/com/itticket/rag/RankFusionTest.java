package com.itticket.rag;

import com.itticket.rag.support.RankFusion;
import com.itticket.rag.vo.ChunkHit;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

/**
 * RRF 融合排序的单元测试。
 *
 * <p>规范关联：服务于 MR-004（specs/10-model-rag-integration.md:70）检索链路的混合召回阶段；
 * 融合只改排序，不得改写余弦相似度——阈值判定（MR-001 · specs/10-model-rag-integration.md:34）
 * 始终基于真实 cosine，故 cosineSimilarityIsCarriedThroughUnchanged 是核心断言。</p>
 * RRF（Reciprocal Rank Fusion，倒数排名融合）双路检索融合排序的单元测试。
 * 向量检索（KNN）与全文检索（text）两路各返回一个有序候选列表，
 * 融合公式 rrf = 1/(k+rank_knn) + 1/(k+rank_text)（未命中的路 rank 记为一档极低分），
 * 两路都命中的切片天然靠前。
 * 本类验证：融合排序的相对次序、topK 截断、分值透传（cosine 不许被融合改写）、
 * 单边命中的路 rank 标记（-1 = 未命中该路）、以及空输入兜底。
 */
public class RankFusionTest {

    private static final BigDecimal COS_HIGH = new BigDecimal("0.9000");
    private static final BigDecimal COS_MID = new BigDecimal("0.7000");

    /**
     * 核心语义：c1 同时出现在两路（knn 第2、text 第2），即使它在单路都不是第1，
     * 也必须压过仅在一路排第1的 c2（KNN 第1）和 c3（text 第1）。
     * 同时锁定融合分递减与两路 rank 值原样记录（前端/审计可展示“双路命中”）。
     */
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

    /** topK=2 时结果截断为前两名，且保持融合分顺序（c1 > c2） */
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

    /** cosine 相似度是“原始证据”，融合只负责重排，绝不允许改写该值（阈值判定依赖原值） */
    @Test
    public void cosineSimilarityIsCarriedThroughUnchanged() {
        ChunkHit hit = ChunkHit.raw("c1", "a1", "v1", "v1", "t", "x", "C_NET", COS_HIGH);

        List<ChunkHit> fused = RankFusion.fuse(List.of(hit), List.of(), 5);

        Assertions.assertEquals(COS_HIGH, fused.get(0).cosineSimilarity(), "融合不得改写相似度");
    }

    /** 仅全文路命中的切片：cosine 保持 null（向量路无证据），textRank=1、knnRank=-1 标记未命中向量路 */
    @Test
    public void textOnlyHitKeepsNullCosine() {
        ChunkHit textOnly = ChunkHit.raw("c1", "a1", "v1", "v1", "t", "x", "C_NET", null);

        List<ChunkHit> fused = RankFusion.fuse(List.of(), List.of(textOnly), 5);

        Assertions.assertNull(fused.get(0).cosineSimilarity());
        Assertions.assertEquals(1, fused.get(0).textRank());
        Assertions.assertEquals(-1, fused.get(0).knnRank());
    }

    /** 空输入与 null 输入都安全返回空列表（上层容错，不抛 NPE） */
    @Test
    public void emptyInputsReturnEmptyResult() {
        Assertions.assertTrue(RankFusion.fuse(List.of(), List.of(), 5).isEmpty());
        Assertions.assertTrue(RankFusion.fuse(null, null, 5).isEmpty());
    }
}