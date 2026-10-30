package com.itticket.consultation.adapter.retrieval;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.service.KnowledgeQueryService;
import java.math.BigDecimal;
import java.util.*;
/** Only highest-score evidence is selected; no duplicated remote threshold configuration. */
public final class RetrievalPolicy {
    private final KnowledgeQueryService knowledge;
    /** 图扩展邻居准入白名单;REPLACES 与共指边在工业共识上不是列证依据,永不入场。 */
    private final Set<String> expansionEdgeWhitelist;
    /** 扩展条目分下限,低于即丢,不影响拒答门。 */
    private final BigDecimal expansionScoreFloor;
    /** 单个源卡可携带的邻居上限。 */
    private final int expansionMaxNeighbors;

    public RetrievalPolicy(KnowledgeQueryService knowledge, Set<String> expansionEdgeWhitelist,
            BigDecimal expansionScoreFloor, int expansionMaxNeighbors) {
        this.knowledge = knowledge;
        this.expansionEdgeWhitelist = Set.copyOf(expansionEdgeWhitelist);
        this.expansionScoreFloor = expansionScoreFloor;
        this.expansionMaxNeighbors = expansionMaxNeighbors;
    }

    public List<RetrievedKnowledge> material(RetrievalResult result, RagCallContext context) {
        validateIdentity(result.items());
        if (!result.reliable()) return List.of();
        Map<String, RetrievedKnowledge> byVersion = new LinkedHashMap<>();
        result.items().stream().filter(item -> item.score() != null &&
                item.score().compareTo(result.topScore()) == 0)
                .sorted(Comparator.comparing(RetrievedKnowledge::chunkId))
                .forEach(item -> byVersion.putIfAbsent(item.versionId(), bounded(item)));
        // 图扩展邻居的准入是五条件取交集,不是任一条件满足就收:
        // ①显式标记 graphExpanded=true ②白名单关系 ③源卡已入基础材料
        // ④分数达到下限 ⑤该源已收邻居数未达上限。任一不满足只丢该条,不产生拒答。
        Set<String> admittedArticles = new HashSet<>();
        byVersion.values().forEach(item -> admittedArticles.add(item.articleId()));
        Map<String, Integer> neighborsBySource = new HashMap<>();
        Map<String, RetrievedKnowledge> expandedByVersion = new LinkedHashMap<>();
        for (RetrievedKnowledge item : result.items()) {
            if (item.graphExpanded() == null || !item.graphExpanded()
                    || item.relation() == null || !expansionEdgeWhitelist.contains(item.relation())
                    || item.expandedFrom() == null || !admittedArticles.contains(item.expandedFrom())
                    || item.score() == null || item.score().compareTo(expansionScoreFloor) < 0
                    || neighborsBySource.getOrDefault(item.expandedFrom(), 0) >= expansionMaxNeighbors)
                continue;
            RetrievedKnowledge bounded = bounded(item);
            if (expandedByVersion.putIfAbsent(item.versionId(), bounded) == null)
                neighborsBySource.merge(item.expandedFrom(), 1, Integer::sum);
        }
        List<RetrievedKnowledge> material = new ArrayList<>();
        material.addAll(byVersion.values());
        material.addAll(expandedByVersion.values());
        List<RetrievedKnowledge> verified = new ArrayList<>(material.size());
        for (RetrievedKnowledge item : material) {
            context.timeoutMillis(Long.MAX_VALUE);
            boolean current;
            try { current = knowledge.isPublishedCurrentVersion(item.articleId(), item.versionId()); }
            catch (RuntimeException unavailable) {
                throw new DependencyFailure(RagStatus.UNAVAILABLE, "KNOWLEDGE_DATABASE_UNAVAILABLE", false);
            }
            // 基础条目 PUBLISHED 复核失败仍整单拒答;扩展条目复核失败仅丢该条,不影响拒答门。
            if (!current) {
                if (!Boolean.TRUE.equals(item.graphExpanded())) throw new StaleKnowledge();
                continue;
            }
            verified.add(item);
        }
        context.timeoutMillis(Long.MAX_VALUE);
        return List.copyOf(verified);
    }
    private static void validateIdentity(List<RetrievedKnowledge> items) {
        Map<String, String> articles = new HashMap<>();
        Map<String, RetrievedKnowledge> chunks = new HashMap<>();
        for (RetrievedKnowledge item : items) {
            String oldArticle = articles.putIfAbsent(item.versionId(), item.articleId());
            RetrievedKnowledge oldChunk = chunks.putIfAbsent(item.chunkId(), item);
            if (oldArticle != null && !oldArticle.equals(item.articleId()) ||
                    oldChunk != null && !oldChunk.equals(item)) throw DependencyFailure.invalid();
        }
    }
    private static RetrievedKnowledge bounded(RetrievedKnowledge item) {
        String content = truncate(item.content(), 1200);
        return new RetrievedKnowledge(item.chunkId(), item.articleId(), item.versionId(),
                truncate(item.title(), 200), truncate(content, 1000), content,
                item.categoryId(), item.score(), item.indexVersion(),
                item.graphExpanded(), item.expandedFrom(), item.relation());
    }
    private static String truncate(String value, int limit) {
        return value.length() <= limit ? value : value.substring(0, limit);
    }
    public static final class StaleKnowledge extends RuntimeException { }
}
