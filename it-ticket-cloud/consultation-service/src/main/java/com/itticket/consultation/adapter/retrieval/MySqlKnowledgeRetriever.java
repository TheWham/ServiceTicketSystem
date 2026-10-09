package com.itticket.consultation.adapter.retrieval;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.service.KnowledgeQueryService;
import java.math.*;
import java.util.*;
public final class MySqlKnowledgeRetriever implements KnowledgeRetriever {
    private final KnowledgeQueryService knowledge;
    private final ConsultationProperties.Ai ai;
    public MySqlKnowledgeRetriever(KnowledgeQueryService knowledge, ConsultationProperties properties) {
        this.knowledge = knowledge; this.ai = properties.getAi();
    }
    @Override public RetrievalResult retrieve(RagQuery query, RagCallContext context) {
        context.timeoutMillis(ai.getRequestTimeoutMs());
        List<RetrievedKnowledge> items;
        try {
            items = knowledge.retrieve(query.question(), query.categoryId(),
                    query.topK() > 0 ? query.topK() : ai.getTopK()).stream().map(hit -> {
                double raw = hit.getScore();
                BigDecimal score = Double.isFinite(raw) && raw > 0
                        ? BigDecimal.valueOf(raw).divide(BigDecimal.valueOf(raw).add(BigDecimal.ONE), 4, RoundingMode.HALF_UP)
                        : BigDecimal.ZERO;
                String title = hit.getTitle() == null || hit.getTitle().isBlank() ? "(未命名知识)" : hit.getTitle();
                String content = hit.getBody() == null || hit.getBody().isBlank() ? hit.getSummary() : hit.getBody();
                if (content == null || content.isBlank()) content = title;
                return new RetrievedKnowledge(hit.getVersionId(), hit.getArticleId(), hit.getVersionId(),
                        title, content, content, hit.getCategoryId(), score, hit.getVersionId());
            }).toList();
        } catch (RuntimeException unavailable) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "KNOWLEDGE_DATABASE_UNAVAILABLE", false);
        }
        context.timeoutMillis(ai.getRequestTimeoutMs());
        BigDecimal top = items.stream().map(RetrievedKnowledge::score).max(BigDecimal::compareTo).orElse(BigDecimal.ZERO);
        AiRefusalReason reason = !items.isEmpty() && top.compareTo(ai.getLocalRetrievalMinScore()) < 0
                ? AiRefusalReason.LOW_CONFIDENCE : null;
        return new RetrievalResult(OfficeDomain.OFFICE_IT, !items.isEmpty() && reason == null, reason, items, top);
    }
}
