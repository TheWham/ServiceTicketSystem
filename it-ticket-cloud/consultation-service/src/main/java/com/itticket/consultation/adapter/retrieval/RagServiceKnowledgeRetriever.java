package com.itticket.consultation.adapter.retrieval;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.adapter.policy.OfficeDomain;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.enums.*;
import java.math.BigDecimal;
import java.net.URI;
import java.util.*;
/** RAG retrieval HTTP boundary: remote scores and decisions are never reinterpreted as model confidence. */
public final class RagServiceKnowledgeRetriever implements KnowledgeRetriever {
    private final ConsultationProperties.Ai ai;
    private final DependencyHttpClient http;
    private final ObjectMapper json = new ObjectMapper();
    public RagServiceKnowledgeRetriever(ConsultationProperties properties, DependencyHttpClient http) {
        this.ai = properties.getAi(); this.http = http;
    }
    @Override public RetrievalResult retrieve(RagQuery query, RagCallContext context) {
        if (ai.getRagBaseUrl() == null || ai.getRagBaseUrl().isBlank())
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "NOT_CONFIGURED", false);
        ObjectNode body = json.createObjectNode().put("question", query.question())
                .put("topK", query.topK() > 0 ? query.topK() : ai.getTopK());
        if (query.categoryId() != null) body.put("categoryId", query.categoryId());
        JsonNode root = http.post(URI.create(ai.getRagBaseUrl().replaceAll("/+$", "") + "/api/v1/rag/retrievals"),
                body, Map.of("X-User-Id", query.caller().userId(), "X-User-Role", query.caller().role()),
                context, ai.getRagRequestTimeoutMs());
        if (!root.path("code").isIntegralNumber()) throw DependencyFailure.invalid();
        if (root.path("code").intValue() != 0)
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "RAG_BUSINESS_ERROR", false);
        return parse(root.path("data"));
    }
    private RetrievalResult parse(JsonNode data) {
        if (!data.isObject() || !data.path("items").isArray()
                || !data.path("reliable").isBoolean() || !data.path("publishedOnly").isBoolean()
                || !data.path("publishedOnly").booleanValue()) throw DependencyFailure.invalid();
        OfficeDomain domain = enumValue(data.path("domain"), OfficeDomain.class);
        AiReplyType reply = enumValue(data.path("suggestedReplyType"), AiReplyType.class);
        AiRefusalReason reason = data.hasNonNull("suggestedRefusalReason")
                ? enumValue(data.get("suggestedRefusalReason"), AiRefusalReason.class) : null;
        BigDecimal topScore = score(data.path("topScore"), false);
        boolean reliable = data.path("reliable").booleanValue();
        List<RetrievedKnowledge> items = new ArrayList<>();
        for (JsonNode item : data.path("items")) {
            if (!item.isObject()) throw DependencyFailure.invalid();
            String chunk = text(item, "chunkId"), article = text(item, "articleId"),
                    version = text(item, "versionId"), index = text(item, "indexVersion");
            if (!version.equals(index)) throw DependencyFailure.invalid();
            items.add(new RetrievedKnowledge(chunk, article, version, text(item, "title"),
                    text(item, "snippet"), text(item, "content"),
                    nullableText(item.path("categoryId")), score(item.path("score"), true), index));
        }
        BigDecimal maximum = items.stream().map(RetrievedKnowledge::score).filter(Objects::nonNull)
                .max(BigDecimal::compareTo).orElse(BigDecimal.ZERO);
        if (maximum.compareTo(topScore) != 0) throw DependencyFailure.invalid();
        switch (domain) {
            case OFF_TOPIC -> {
                if (reply != AiReplyType.REFUSE || reason != AiRefusalReason.OFF_TOPIC || reliable || !items.isEmpty())
                    throw DependencyFailure.invalid();
            }
            case HIGH_RISK -> {
                if (reply != AiReplyType.REFUSE || reason != AiRefusalReason.HIGH_RISK_TOPIC || reliable || !items.isEmpty())
                    throw DependencyFailure.invalid();
            }
            case UNCERTAIN -> {
                if (reply != AiReplyType.CLARIFY || reason != null || reliable || !items.isEmpty())
                    throw DependencyFailure.invalid();
            }
            case OFFICE_IT -> {
                if ((reason == null && reply != AiReplyType.ANSWER) ||
                        (reason != null && (reply != AiReplyType.REFUSE || reliable)) ||
                        (reliable && (items.isEmpty() || topScore.signum() <= 0)) ||
                        reason == AiRefusalReason.OFF_TOPIC || reason == AiRefusalReason.HIGH_RISK_TOPIC)
                    throw DependencyFailure.invalid();
            }
        }
        if (reason == AiRefusalReason.MODEL_UNAVAILABLE)
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "RAG_DEPENDENCY_UNAVAILABLE", true);
        return new RetrievalResult(domain, reliable, reason, items, topScore);
    }
    private static String text(JsonNode node, String field) {
        JsonNode value = node.path(field);
        if (!value.isTextual() || value.textValue().isBlank()) throw DependencyFailure.invalid();
        return value.textValue();
    }
    private static String nullableText(JsonNode value) {
        if (value.isNull() || value.isMissingNode()) return null;
        if (!value.isTextual()) throw DependencyFailure.invalid();
        return value.textValue();
    }
    private static BigDecimal score(JsonNode value, boolean nullable) {
        if (nullable && (value.isNull() || value.isMissingNode())) return null;
        if (!value.isNumber() || value.decimalValue().signum() < 0 ||
                value.decimalValue().compareTo(BigDecimal.ONE) > 0) throw DependencyFailure.invalid();
        return value.decimalValue();
    }
    private static <E extends Enum<E>> E enumValue(JsonNode value, Class<E> type) {
        if (!value.isTextual()) throw DependencyFailure.invalid();
        try { return Enum.valueOf(type, value.textValue()); }
        catch (IllegalArgumentException invalid) { throw DependencyFailure.invalid(); }
    }
}
