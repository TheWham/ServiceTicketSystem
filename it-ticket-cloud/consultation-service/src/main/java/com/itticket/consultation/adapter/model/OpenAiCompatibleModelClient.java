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

    /** SSE 流内聚合器:全文累积 + finish_reason/[DONE] 收口状态,帧畸形立即拒绝。 */
    private final class SseAccumulator {
        final StringBuilder full = new StringBuilder();
        String finishReason;
        boolean done;

        void consume(String line, StreamingJsonExtractor extractor) {
            if (line == null || line.isBlank() || !line.startsWith("data:")) return; // 忽略空行/注释/事件头
            String payload = line.substring("data:".length()).strip();
            if ("[DONE]".equals(payload)) {
                done = true;
                return;
            }
            JsonNode frame;
            try {
                frame = json.readTree(payload);
            } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) {
                throw DependencyFailure.invalid();
            }
            if (frame == null || !frame.isObject()) throw DependencyFailure.invalid();
            JsonNode choices = frame.path("choices");
            if (!choices.isArray() || choices.size() != 1) throw DependencyFailure.invalid();
            JsonNode choice = choices.get(0), delta = choice.path("delta");
            if (!delta.isObject()) throw DependencyFailure.invalid();
            if (delta.hasNonNull("tool_calls") || delta.hasNonNull("function_call")) throw DependencyFailure.invalid();
            JsonNode content = delta.path("content");
            if (content.isTextual()) {
                full.append(content.textValue());
                extractor.feed(content.textValue());
            } else if (!content.isMissingNode() && !content.isNull()) {
                throw DependencyFailure.invalid();
            }
            JsonNode reason = choice.path("finish_reason");
            if (reason.isTextual()) finishReason = reason.textValue();
        }
    }

    /**
     * 与 {@link #complete} 同输入的流式变体:body stream:true,SSE 增量 delta.content
     * 累积为全文,其中 answerText 片段经 extractor 即时解码后交给 tokenSink(打字机);
     * [DONE] 且 finish_reason=stop 才收口,否则 INVALID_RESPONSE——不静默接受截断响应。
     * 返回完整六键 JsonNode,六键校验仍在 AnswerGenerator。
     */
    public JsonNode completeStream(String policy, String input, int maxTokens, RagCallContext context,
                                   java.util.function.Consumer<String> tokenSink) {
        if (ai.getBaseUrl() == null || ai.getBaseUrl().isBlank() ||
                ai.getApiKey() == null || ai.getApiKey().isBlank())
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "NOT_CONFIGURED", false);
        ObjectNode body = json.createObjectNode().put("model", ai.getModel())
                .put("temperature", ai.getTemperature()).put("max_tokens", maxTokens).put("stream", true);
        body.putObject("response_format").put("type", "json_object");
        ArrayNode messages = body.putArray("messages");
        messages.addObject().put("role", "system").put("content", policy);
        messages.addObject().put("role", "user").put("content", input);
        String base = ai.getBaseUrl().replaceAll("/+$", "");
        SseAccumulator sse = new SseAccumulator();
        StreamingJsonExtractor extractor = new StreamingJsonExtractor(tokenSink);
        http.postStream(URI.create(base + "/chat/completions"), body,
                Map.of("Authorization", "Bearer " + ai.getApiKey()), context, ai.getRequestTimeoutMs(),
                line -> sse.consume(line, extractor));
        if (!sse.done || !"stop".equals(sse.finishReason)) throw DependencyFailure.invalid();
        try {
            JsonNode result = json.readTree(sse.full.toString());
            if (result == null || !result.isObject()) throw DependencyFailure.invalid();
            return result;
        } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) { throw DependencyFailure.invalid(); }
    }
}