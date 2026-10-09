package com.itticket.consultation.adapter.retrieval;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.enums.AiRefusalReason;
import java.math.BigDecimal;
import java.util.List;
/** Successful retrieval; failures use DependencyFailure, never empty-success fallbacks. */
public record RetrievalResult(OfficeDomain domain, boolean reliable, AiRefusalReason refusalReason,
        List<RetrievedKnowledge> items, BigDecimal topScore) {
    public RetrievalResult { items = List.copyOf(items); }
}
