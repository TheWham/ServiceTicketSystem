package com.itticket.consultation.adapter.model;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.*;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.config.ConsultationProperties;
import java.net.URI;
import java.util.Map;
public final class OpenAiCompatibleModelClient {
    private final ConsultationProperties.Ai ai;
    private final DependencyHttpClient http;
    private final ObjectMapper json = new ObjectMapper();
    public OpenAiCompatibleModelClient(ConsultationProperties properties, DependencyHttpClient http) {
        this.ai = properties.getAi(); this.http = http;
    }
    public int maxOutputTokens() { return ai.getMaxOutputTokens(); }
    public String modelVersion() { return ai.getModel(); }
    public JsonNode complete(String policy, String input, int maxTokens, RagCallContext context) {
        if (ai.getBaseUrl() == null || ai.getBaseUrl().isBlank() ||
                ai.getApiKey() == null || ai.getApiKey().isBlank())
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "NOT_CONFIGURED", false);
        ObjectNode body = json.createObjectNode().put("model", ai.getModel())
                .put("temperature", ai.getTemperature()).put("max_tokens", maxTokens).put("stream", false);
        body.putObject("response_format").put("type", "json_object");
        ArrayNode messages = body.putArray("messages");
        messages.addObject().put("role", "system").put("content", policy);
        messages.addObject().put("role", "user").put("content", input);
        String base = ai.getBaseUrl().replaceAll("/+$", "");
        JsonNode root = http.post(URI.create(base + "/chat/completions"), body,
                Map.of("Authorization", "Bearer " + ai.getApiKey()), context, ai.getRequestTimeoutMs());
        JsonNode choices = root.path("choices");
        if (!choices.isArray() || choices.size() != 1) throw DependencyFailure.invalid();
        JsonNode choice = choices.get(0), message = choice.path("message"), content = message.path("content");
        if (!"stop".equals(choice.path("finish_reason").asText()) ||
                message.hasNonNull("tool_calls") || message.hasNonNull("function_call") || !content.isTextual())
            throw DependencyFailure.invalid();
        try {
            JsonNode result = json.readTree(content.textValue());
            if (result == null || !result.isObject()) throw DependencyFailure.invalid();
            return result;
        } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) { throw DependencyFailure.invalid(); }
    }
}
