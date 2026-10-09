package com.itticket.consultation.adapter.retrieval;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.service.KnowledgeQueryService;
import java.util.*;
/** Only highest-score evidence is selected; no duplicated remote threshold configuration. */
public final class RetrievalPolicy {
    private final KnowledgeQueryService knowledge;
    public RetrievalPolicy(KnowledgeQueryService knowledge) { this.knowledge = knowledge; }
    public List<RetrievedKnowledge> material(RetrievalResult result, RagCallContext context) {
        validateIdentity(result.items());
        if (!result.reliable()) return List.of();
        Map<String, RetrievedKnowledge> byVersion = new LinkedHashMap<>();
        result.items().stream().filter(item -> item.score() != null &&
                item.score().compareTo(result.topScore()) == 0)
                .sorted(Comparator.comparing(RetrievedKnowledge::chunkId))
                .forEach(item -> byVersion.putIfAbsent(item.versionId(), bounded(item)));
        List<RetrievedKnowledge> material = List.copyOf(byVersion.values());
        for (RetrievedKnowledge item : material) {
            context.timeoutMillis(Long.MAX_VALUE);
            boolean current;
            try { current = knowledge.isPublishedCurrentVersion(item.articleId(), item.versionId()); }
            catch (RuntimeException unavailable) {
                throw new DependencyFailure(RagStatus.UNAVAILABLE, "KNOWLEDGE_DATABASE_UNAVAILABLE", false);
            }
            if (!current) throw new StaleKnowledge();
        }
        context.timeoutMillis(Long.MAX_VALUE);
        return material;
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
                item.categoryId(), item.score(), item.indexVersion());
    }
    private static String truncate(String value, int limit) {
        return value.length() <= limit ? value : value.substring(0, limit);
    }
    public static final class StaleKnowledge extends RuntimeException { }
}
