package com.itticket.consultation.adapter.retrieval;

import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.service.KnowledgeQueryService;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 图扩展条目的显式准入谓词与 PUBLISHED 复核语义(Task 12)。
 *
 * <p>五条件全部满足才收,任一条件不满足 → 仅丢弃该扩展条目,基础材料不受影响;
 * 基础条目仍按 score==topScore 准入、topScore 只在基础条目中计算;
 * 基础条目 not-current 仍整单拒答(StaleKnowledge 语义不回归),
 * 扩展条目 not-current 只是质量门,丢弃该条而非拒答。</p>
 */
class RetrievalPolicyGraphExpansionTest {

    /** 与 python 侧 rag_pipeline.config.ExpansionConfig 默认一致的谓词参数。 */
    private static final Set<String> WHITELIST = Set.of("SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES");
    private static final BigDecimal FLOOR = new BigDecimal("0.10");

    private final KnowledgeQueryService knowledge = mock(KnowledgeQueryService.class);
    private final RetrievalPolicy policy = new RetrievalPolicy(knowledge, WHITELIST, FLOOR, 2);

    /** 金标 ①:低分扩展条目在五条件全满足时到达生成器,基础与扩展并存。 */
    @Test
    void lowScoreExpandedNeighborReachesGeneratorWhenAllConditionsHold() {
        current("A1", "V1");
        current("A2", "V2");
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                expanded("C2", "A2", "V2", "0.4", "RELATED", "A1")), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId)
                .containsExactly("C1", "C2");
        assertThat(material.get(1).graphExpanded()).isTrue();
        assertThat(material.get(1).expandedFrom()).isEqualTo("A1");
        assertThat(material.get(1).relation()).isEqualTo("RELATED");
        assertThat(material.get(1).score()).isEqualByComparingTo("0.4");
    }

    /** 金标 ②:未过 PUBLISHED 的扩展条目被丢弃,不抛 StaleKnowledge,基础条目仍在。 */
    @Test
    void expandedNeighborFailingPublishedCheckIsDroppedWithoutRefusingWholeAnswer() {
        current("A1", "V1");
        when(knowledge.isPublishedCurrentVersion("A2", "V2")).thenReturn(false);
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                expanded("C2", "A2", "V2", "0.4", "RELATED", "A1")), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId).containsExactly("C1");
    }

    /** 金标 ③:relation=REPLACES 的扩展条目永不到达生成器(python 侧之外的第二道独立防线)。 */
    @Test
    void replacesNeighborNeverReachesTheGenerator() {
        current("A1", "V1");
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                expanded("C2", "A2", "V2", "0.4", "REPLACES", "A1")), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId).containsExactly("C1");
    }

    /** 条件 ①:未标记为 graphExpanded 的低分条目不入扩展分支,也不构成基础条目(score 低于 topScore)。 */
    @Test
    void unmarkedLowScoreItemIsNeverAdmitted() {
        current("A1", "V1");
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                unmarked("C2", "A2", "V2", "0.4", null),
                unmarked("C3", "A3", "V3", "0.35", Boolean.FALSE)), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId).containsExactly("C1");
    }

    /** 条件 ②:白名单外的 relation(null 也算白名单外)不收。 */
    @Test
    void expandedOutsideWhitelistRelationIsDropped() {
        current("A1", "V1");
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                expanded("C2", "A2", "V2", "0.4", "SUPPORTS_TICKET", "A1"),
                expanded("C3", "A3", "V3", "0.4", null, "A1")), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId).containsExactly("C1");
    }

    /** 条件 ③:源卡未准入(expandedFrom 不在基础材料)的扩展条目不收。 */
    @Test
    void expandedWithoutAdmittedSourceIsDropped() {
        current("A1", "V1");
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                expanded("C2", "A2", "V2", "0.4", "RELATED", "A9")), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId).containsExactly("C1");
    }

    /** 条件 ④:低于 expansionScoreFloor 的扩展条目不收。 */
    @Test
    void expandedBelowScoreFloorIsDropped() {
        current("A1", "V1");
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                expanded("C2", "A2", "V2", "0.05", "RELATED", "A1")), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId).containsExactly("C1");
    }

    /** 条件 ⑤:同一源已收满 expansionMaxNeighbors 后的邻居条目不收,基础与其他邻居不受影响。 */
    @Test
    void expandedOverSourceNeighborCapIsDropped() {
        current("A1", "V1");
        current("A2", "V2");
        current("A3", "V3");
        List<RetrievedKnowledge> material = policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8"),
                expanded("C2", "A2", "V2", "0.4", "RELATED", "A1"),
                expanded("C3", "A3", "V3", "0.35", "PROCESS_APPLIES", "A1"),
                expanded("C4", "A4", "V4", "0.3", "SAME_ROOT_CAUSE", "A1")), "0.8"), context());
        assertThat(material).extracting(RetrievedKnowledge::chunkId)
                .containsExactly("C1", "C2", "C3");
    }

    /** 语义不回归:基础条目 not-current 仍整单拒答。 */
    @Test
    void baseNotCurrentStillRefusesWholeAnswer() {
        when(knowledge.isPublishedCurrentVersion("A1", "V1")).thenReturn(false);
        assertThatThrownBy(() -> policy.material(result(List.of(
                base("C1", "A1", "V1", "0.8")), "0.8"), context()))
                .isInstanceOf(RetrievalPolicy.StaleKnowledge.class);
    }

    /** 装配默认值与 python 侧 rag_pipeline.config.ExpansionConfig 一致(防配置漂移)。 */
    @Test
    void configDefaultsMatchThePythonSide() {
        ConsultationProperties.GraphExpansion expansion =
                new ConsultationProperties().getAi().getGraphExpansion();
        assertThat(expansion.getEdgeWhitelist())
                .containsExactlyInAnyOrder("SAME_ROOT_CAUSE", "RELATED", "PROCESS_APPLIES");
        assertThat(expansion.getScoreFloor()).isEqualByComparingTo("0.10");
        assertThat(expansion.getMaxNeighbors()).isEqualTo(2);
    }

    private void current(String article, String version) {
        when(knowledge.isPublishedCurrentVersion(article, version)).thenReturn(true);
    }

    private static RetrievalResult result(List<RetrievedKnowledge> items, String topScore) {
        return new RetrievalResult(OfficeDomain.OFFICE_IT, true, null, items, new BigDecimal(topScore));
    }

    private static RagCallContext context() {
        return new RagCallContext("graph-test", System.nanoTime() + 5_000_000_000L, new RagExecutionAudit());
    }

    private static RetrievedKnowledge base(String chunk, String article, String version, String score) {
        return new RetrievedKnowledge(chunk, article, version, "标题", "摘要", "正文", "C_NET",
                new BigDecimal(score), version, null, null, null);
    }

    private static RetrievedKnowledge expanded(String chunk, String article, String version,
            String score, String relation, String expandedFrom) {
        return new RetrievedKnowledge(chunk, article, version, "标题", "摘要", "正文", "C_NET",
                new BigDecimal(score), version, Boolean.TRUE, expandedFrom, relation);
    }

    private static RetrievedKnowledge unmarked(String chunk, String article, String version,
            String score, Boolean graphExpanded) {
        return new RetrievedKnowledge(chunk, article, version, "标题", "摘要", "正文", "C_NET",
                new BigDecimal(score), version, graphExpanded, "A1", "RELATED");
    }
}
