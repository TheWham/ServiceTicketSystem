package com.itticket.consultation.adapter.agent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.TicketDraftDto;

import java.net.URI;
import java.util.List;
import java.util.Map;

/**
 * Python agent_service 客户端。
 *
 * <p>Function Calling（ReAct 循环 + 白名单工具）已下沉到 Python `agent_service`
 * （`services/python-retrieval/agent_service`，`POST /api/v1/agent/chat`，端口 8320）。
 * 本类只负责:把问题、历史、预检索材料与已认证主体（X-User-Id/Role）传给 Python,
 * 取回结构化生成结果（6 键 JSON）与带外建单草稿。
 *
 * <p>引用守卫、会话状态、建单确认仍由 Java 侧负责（ComposedRagAdapter / AiAnswerGuard /
 * ConsultationService.confirmTicketDraft）——Python 只负责「脑+手」，Java 负责「门禁+账本」。
 */
public final class PythonAgentClient {

    private static final long REQUEST_TIMEOUT_MS = 60000L;

    private final ConsultationProperties.Agent agent;
    private final DependencyHttpClient http;
    private final ObjectMapper json = new ObjectMapper();

    public PythonAgentClient(ConsultationProperties properties, DependencyHttpClient http) {
        this.agent = properties.getAi().getAgent();
        this.http = http;
    }

    /** 是否启用（开关打开且配了 Python agent 地址）。 */
    public boolean enabled() {
        return agent.isEnabled() && agent.getServiceBaseUrl() != null && !agent.getServiceBaseUrl().isBlank();
    }

    /** 调用 Python agent 跑一轮 ReAct 生成。 */
    public AgentResult chat(RagQuery query, List<RetrievedKnowledge> material, RagCallContext context) {
        ObjectNode body = json.createObjectNode().put("question", query.question());
        ArrayNode history = body.putArray("history");
        for (RagQuery.Turn turn : query.priorTurns()) {
            history.addObject().put("role", turn.role()).put("content", turn.content());
        }
        ArrayNode materials = body.putArray("material");
        for (RetrievedKnowledge item : material) {
            materials.addObject().put("versionId", item.versionId())
                    .put("title", item.title() == null ? "" : item.title())
                    .put("content", item.content() == null ? "" : item.content());
        }
        if (query.categoryId() != null) body.put("categoryId", query.categoryId());
        if (query.assetId() != null) body.put("assetId", query.assetId());

        String base = agent.getServiceBaseUrl().replaceAll("/+$", "");
        JsonNode root = http.post(URI.create(base + "/api/v1/agent/chat"), body,
                Map.of("X-User-Id", query.caller().userId(), "X-User-Role", query.caller().role()),
                context, REQUEST_TIMEOUT_MS);
        if (!root.path("code").isIntegralNumber()) throw DependencyFailure.invalid();
        if (root.path("code").intValue() != 0) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "AGENT_BUSINESS_ERROR", false);
        }
        JsonNode data = root.path("data");
        if (!data.isObject()) throw DependencyFailure.invalid();
        return new AgentResult(data, draftOf(data.path("ticketDraft")));
    }

    private static TicketDraftDto draftOf(JsonNode node) {
        if (!node.isObject()) return null;
        String title = text(node, "title");
        String description = text(node, "description");
        if (title.isBlank() && description.isBlank()) return null;
        return new TicketDraftDto(title, nullableText(node, "category"), description,
                text(node, "priority").isBlank() ? "MEDIUM" : text(node, "priority"));
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.path(field);
        return value.isTextual() ? value.textValue() : "";
    }

    private static String nullableText(JsonNode node, String field) {
        String value = text(node, field);
        return value.isBlank() ? null : value;
    }

    /** 结果:payload 为 6 键生成 JSON, draft 为带外建单草稿(无则 null)。 */
    public record AgentResult(JsonNode payload, TicketDraftDto draft) {
    }
}