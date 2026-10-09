package com.itticket.consultation.adapter;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.KnowledgeHit;
import com.itticket.consultation.enums.AiRefusalReason;
import com.itticket.consultation.enums.AiReplyType;

import java.math.BigDecimal;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** RAG 检索契约边界。只传递认证主体与请求 ID，不依赖工作线程的 ThreadLocal。 */
public final class RagServiceClient {
    private static final ObjectMapper JSON = new ObjectMapper();
    private final ConsultationProperties properties;
    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3)).followRedirects(HttpClient.Redirect.NEVER).build();

    public RagServiceClient(ConsultationProperties properties) { this.properties = properties; }

    /** decision 非空时必须短路，禁止降级成空知识后继续生成。 */
    public record Retrieval(List<KnowledgeHit> hits, RagResult decision) { }

    public Retrieval retrieve(RagQuery query, String requestId) {
        return retrieve(query, requestId, false);
    }

    /** 仅供生成适配器完成当前会话语义分类后调用，旧词表/相似度判定不覆盖已确认的 IT 意图。 */
    Retrieval retrieveForClassifiedIt(RagQuery query, String requestId) {
        return retrieve(query, requestId, true);
    }

    private Retrieval retrieve(RagQuery query, String requestId, boolean classifiedIt) {
        long started = System.nanoTime();
        try {
            if (blank(query.callerId()) || blank(query.callerRole())) {
                return failure(RagStatus.UNAVAILABLE, "RAG_AUTH_MISSING", started);
            }
            String base = properties.getAi().getRagBaseUrl();
            if (blank(base)) return failure(RagStatus.UNAVAILABLE, "RAG_NOT_CONFIGURED", started);
            URI uri = URI.create(base.replaceAll("/+$", "") + "/api/v1/rag/retrievals");
            if (!List.of("http", "https").contains(uri.getScheme()) || uri.getHost() == null
                    || uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null) {
                return failure(RagStatus.UNAVAILABLE, "RAG_NOT_CONFIGURED", started);
            }
            ObjectNode body = JSON.createObjectNode().put("question", query.question())
                    .put("topK", Math.min(20, Math.max(1, query.topK())));
            if (!blank(query.categoryId())) body.put("categoryId", query.categoryId());
            HttpRequest request = HttpRequest.newBuilder(uri)
                    .header("Content-Type", "application/json; charset=utf-8")
                    .header("X-User-Id", query.callerId())
                    .header("X-User-Role", query.callerRole())
                    .header("X-Request-Id", requestId == null ? "" : requestId)
                    .timeout(Duration.ofMillis(Math.max(1, properties.getAi().getRetrievalTimeoutMs())))
                    .POST(HttpRequest.BodyPublishers.ofString(body.toString())).build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) {
                String reason = response.statusCode() == 401 || response.statusCode() == 403 ? "RAG_AUTH_FAILED"
                        : response.statusCode() == 429 ? "RAG_RATE_LIMITED" : "RAG_HTTP_FAILURE";
                return failure(RagStatus.UNAVAILABLE, reason, started);
            }
            JsonNode envelope = JSON.readTree(response.body());
            if (envelope == null || !envelope.path("code").isIntegralNumber()) {
                return failure(RagStatus.INVALID_RESPONSE, "RAG_INVALID_RESPONSE", started);
            }
            if (envelope.path("code").asInt() != 0) return failure(RagStatus.UNAVAILABLE, "RAG_BUSINESS_FAILURE", started);
            return decode(envelope.path("data"), started, classifiedIt);
        } catch (HttpTimeoutException e) {
            return failure(RagStatus.TIMEOUT, "RAG_TIMEOUT", started);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return failure(RagStatus.UNAVAILABLE, "RAG_INTERRUPTED", started);
        } catch (JsonProcessingException | IllegalArgumentException e) {
            return failure(RagStatus.INVALID_RESPONSE, "RAG_INVALID_RESPONSE", started);
        } catch (java.io.IOException e) {
            return failure(RagStatus.UNAVAILABLE, "RAG_UNAVAILABLE", started);
        }
    }

    private Retrieval decode(JsonNode data, long started, boolean classifiedIt) {
        if (!data.isObject() || !data.path("publishedOnly").isBoolean() || !data.path("publishedOnly").asBoolean()
                || !data.path("reliable").isBoolean() || !data.path("items").isArray()) return invalid(started);
        BigDecimal score = score(data.path("topScore"));
        if (score == null) return invalid(started);
        String domain = data.path("domain").asText();
        if (!List.of("OFFICE_IT", "OFF_TOPIC", "HIGH_RISK", "UNCERTAIN").contains(domain)) return invalid(started);
        JsonNode reasonNode = data.path("suggestedRefusalReason");
        AiRefusalReason reason = null;
        if (!reasonNode.isMissingNode() && !reasonNode.isNull()) {
            if (!reasonNode.isTextual()) return invalid(started);
            try { reason = AiRefusalReason.valueOf(reasonNode.asText()); }
            catch (IllegalArgumentException e) { return invalid(started); }
            if (reason == AiRefusalReason.MODEL_UNAVAILABLE) return failure(RagStatus.UNAVAILABLE, "RAG_DEPENDENCY_UNAVAILABLE", started);
            if (reason == AiRefusalReason.CONFLICTING_KNOWLEDGE) return refuse(reason, score, started);
        }
        // 分类已在模型侧结合完整上下文完成。RAG 的旧关键词规则可能将“周报文件打不开”
        // 或普通自助找回密码误判。此时没有可用知识，允许通用回答，不把被拦截的片段作为引用。
        if (classifiedIt && (("OFF_TOPIC".equals(domain) && reason == AiRefusalReason.OFF_TOPIC)
                || ("HIGH_RISK".equals(domain) && reason == AiRefusalReason.HIGH_RISK_TOPIC)
                || ("OFFICE_IT".equals(domain) && reason == AiRefusalReason.LOW_CONFIDENCE))) {
            if (!"REFUSE".equals(data.path("suggestedReplyType").asText())) return invalid(started);
            return new Retrieval(List.of(), null);
        }
        if ("OFF_TOPIC".equals(domain)) return refuse(AiRefusalReason.OFF_TOPIC, score, started);
        if ("HIGH_RISK".equals(domain)) return refuse(AiRefusalReason.HIGH_RISK_TOPIC, score, started);
        if ("UNCERTAIN".equals(domain)) {
            if (classifiedIt) {
                if (reason != null || !"CLARIFY".equals(data.path("suggestedReplyType").asText())) return invalid(started);
                return new Retrieval(List.of(), null);
            }
            return new Retrieval(List.of(), new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY,
                    "请补充遇到问题的办公设备或应用、具体表现及错误提示，我会根据这些信息继续排查。",
                    List.of(), BigDecimal.ONE, false, null, List.of(), elapsed(started), null));
        }
        if (reason != null) return refuse(reason, score, started);
        if (!"ANSWER".equals(data.path("suggestedReplyType").asText())) return invalid(started);
        // 无命中/不相关资料不进入提示词，更不能挂载成通用回答的来源。
        if (!data.path("reliable").asBoolean()) return new Retrieval(List.of(), null);
        Map<String, KnowledgeHit> hits = new LinkedHashMap<>();
        for (JsonNode item : data.path("items")) {
            if (!text(item, "articleId") || !text(item, "versionId") || !text(item, "title")
                    || !text(item, "snippet") || !text(item, "content") || !text(item, "indexVersion")
                    || !item.path("versionId").asText().equals(item.path("indexVersion").asText())) return invalid(started);
            // BM25-only 记录没有余弦分，不可伪造分数作为可靠引用。
            if (item.path("score").isNull()) continue;
            BigDecimal itemScore = score(item.path("score"));
            if (itemScore == null) return invalid(started);
            if (itemScore.compareTo(properties.getAi().getRagCitationMinScore()) < 0) continue;
            KnowledgeHit hit = new KnowledgeHit();
            hit.setArticleId(item.path("articleId").asText());
            hit.setVersionId(item.path("versionId").asText());
            hit.setTitle(item.path("title").asText());
            hit.setSummary(item.path("snippet").asText());
            hit.setBody(item.path("content").asText());
            hit.setCategoryId(item.path("categoryId").asText(null));
            hit.setScore(itemScore.doubleValue());
            KnowledgeHit previous = hits.get(hit.getVersionId());
            if (previous != null && !previous.getArticleId().equals(hit.getArticleId())) return invalid(started);
            if (previous == null || previous.getScore() < hit.getScore()) hits.put(hit.getVersionId(), hit);
        }
        if (hits.isEmpty()) return invalid(started);
        return new Retrieval(hits.values().stream().sorted(Comparator.comparingDouble(KnowledgeHit::getScore).reversed()).toList(), null);
    }

    private static Retrieval refuse(AiRefusalReason reason, BigDecimal score, long started) {
        return new Retrieval(List.of(), new RagResult(RagStatus.SUCCESS, AiReplyType.REFUSE, null,
                List.of(), score, reason == AiRefusalReason.CONFLICTING_KNOWLEDGE, null, List.of(),
                elapsed(started), null, false, reason == AiRefusalReason.OFF_TOPIC,
                reason == AiRefusalReason.HIGH_RISK_TOPIC, reason));
    }
    private static Retrieval invalid(long started) { return failure(RagStatus.INVALID_RESPONSE, "RAG_INVALID_RESPONSE", started); }
    private static Retrieval failure(RagStatus status, String reason, long started) {
        return new Retrieval(List.of(), RagResult.degraded(status, reason, elapsed(started)));
    }
    private static BigDecimal score(JsonNode node) {
        if (!node.isNumber()) return null;
        BigDecimal value = node.decimalValue();
        return value.signum() < 0 || value.compareTo(BigDecimal.ONE) > 0 ? null : value;
    }
    private static boolean text(JsonNode node, String field) { return node.path(field).isTextual() && !node.path(field).asText().isBlank(); }
    private static boolean blank(String value) { return value == null || value.isBlank(); }
    private static long elapsed(long start) { return (System.nanoTime() - start) / 1_000_000; }
}
