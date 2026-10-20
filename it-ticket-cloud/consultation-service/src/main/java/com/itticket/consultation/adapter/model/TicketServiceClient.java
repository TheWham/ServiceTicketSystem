package com.itticket.consultation.adapter.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.config.ConsultationProperties;

import java.net.URI;
import java.util.Map;

/**
 * ticket-service 内部接口客户端(仅「确认建单」用)。
 *
 * <p>工单是 ticket-service 的事实源,咨询域不得跨库读 {@code ticket} 表(架构 8.1)。
 * AI 的查询/建单草稿在 Python agent_service 里执行(其工具直接调 ticket-service 内部接口);
 * 本类只服务 Java 侧的「员工确认草稿后真正建单」这一步。
 *
 * <p>归属安全(AX-001):{@code creator_id} 由服务端从已认证主体取,不接受请求体指定。
 */
public final class TicketServiceClient {

    private static final long REQUEST_TIMEOUT_MS = 5000L;

    private final ConsultationProperties.Agent agent;
    private final DependencyHttpClient http;
    private final ObjectMapper json = new ObjectMapper();

    public TicketServiceClient(ConsultationProperties properties, DependencyHttpClient http) {
        this.agent = properties.getAi().getAgent();
        this.http = http;
    }

    /** 员工确认后建单,返回新工单号。 */
    public String createTicket(String userId, String role, String title, String category, String description,
                               String priority, String clientToken, RagCallContext ctx) {
        ObjectNode body = json.createObjectNode()
                .put("creator_id", userId)
                .put("title", title)
                .put("description", description);
        if (category != null && !category.isBlank()) body.put("category", category.trim());
        if (priority != null && !priority.isBlank()) body.put("priority", priority.trim());
        if (clientToken != null && !clientToken.isBlank()) body.put("client_token", clientToken);
        JsonNode data = dataOf(http.post(URI.create(endpoint()), body, headers(userId, role),
                ctx, REQUEST_TIMEOUT_MS));
        String ticketId = data.path("ticket_id").asText("");
        if (ticketId.isBlank()) throw DependencyFailure.invalid();
        return ticketId;
    }

    private String endpoint() {
        String base = agent.getTicketServiceBaseUrl();
        if (base == null || base.isBlank()) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "TICKET_SERVICE_NOT_CONFIGURED", false);
        }
        return base.replaceAll("/+$", "") + "/api/internal/tickets";
    }

    private static Map<String, String> headers(String userId, String role) {
        return Map.of("X-User-Id", userId == null ? "" : userId,
                "X-User-Role", role == null ? "" : role);
    }

    private static JsonNode dataOf(JsonNode root) {
        if (!root.path("code").isIntegralNumber()) throw DependencyFailure.invalid();
        if (root.path("code").intValue() != 0) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "TICKET_BUSINESS_ERROR", false);
        }
        return root.path("data");
    }
}