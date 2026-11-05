package com.itticket.consultation.adapter.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagStatus;
import com.itticket.consultation.config.ConsultationProperties;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowableOfType;

/**
 * Task 2 RED:模型客户端流式化。
 * 红线:token 回调按上游分片节流,answerText 增量解码后外发;收口后返回完整六键 JsonNode;
 * 冷状态码/超时错误语义与 complete() 完全一致,无新枚举;帧畸形立即 INVALID_RESPONSE,不静默。
 */
class OpenAiCompatibleModelClientStreamTest {

    private final ObjectMapper om = new ObjectMapper();
    private HttpServer server;

    @AfterEach
    void stop() {
        if (server != null) server.stop(0);
    }

    // ======== 装配 ========

    private static ConsultationProperties config(String baseUrl) {
        ConsultationProperties properties = new ConsultationProperties();
        properties.getAi().setBaseUrl(baseUrl);
        properties.getAi().setApiKey("test-token");
        properties.getAi().setRequestTimeoutMs(3000);
        return properties;
    }

    private static RagCallContext context() {
        return new RagCallContext("req-1", System.nanoTime() + 60_000_000_000L, new RagExecutionAudit());
    }

    private HttpServer start(ThrowingHandler handler) throws IOException {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/chat/completions", exchange -> {
            try {
                handler.handle(exchange);
            } catch (RuntimeException failure) {
                throw failure;
            } catch (Exception failure) {
                throw new IllegalStateException(failure);
            }
        });
        server.start();
        return server;
    }

    @FunctionalInterface
    private interface ThrowingHandler {
        void handle(com.sun.net.httpserver.HttpExchange exchange) throws Exception;
    }

    private ObjectNode frame(String content, String role, String finish, boolean withToolCalls) {
        ObjectNode frame = om.createObjectNode();
        ObjectNode choice = frame.putArray("choices").addObject();
        ObjectNode delta = choice.putObject("delta");
        if (role != null) delta.put("role", role);
        if (content != null) delta.put("content", content);
        if (withToolCalls) delta.putArray("tool_calls");
        if (finish == null) choice.putNull("finish_reason");
        else choice.put("finish_reason", finish);
        return frame;
    }

    private void writeSse(OutputStream body, List<String> payloads) throws IOException {
        for (String payload : payloads) {
            body.write(("data: " + payload + "\n\n").getBytes(StandardCharsets.UTF_8));
            body.flush();
        }
    }

    /** 模型按六键 JSON 输出;此处把完整 JSON 切成两个分片,切点落在 answerText 内部("第一步"之后)。 */
    private List<String> answerFragments(String fullJson) {
        int cut = fullJson.indexOf("第一步") + "第一步".length();
        return List.of(fullJson.substring(0, cut), fullJson.substring(cut));
    }

    private String sixKeyAnswerJson() {
        ObjectNode six = om.createObjectNode();
        six.put("replyType", "ANSWER");
        six.put("answerText", "第一步\n第二步");
        six.putArray("usedVersionIds").add("V1");
        six.put("confidence", 0.90);
        six.put("knowledgeConflict", false);
        six.put("offTopic", false);
        return six.toString();
    }

    private OpenAiCompatibleModelClient streamClient(ConsultationProperties properties) {
        return new OpenAiCompatibleModelClient(properties, new DependencyHttpClient());
    }

    // ======== 用例 ========

    @Test
    void streamEmitsDecodedAnswerTokensThenReturnsSixKeyNode() throws Exception {
        String full = sixKeyAnswerJson();
        List<String> fragments = answerFragments(full);
        List<String> tokens = new ArrayList<>();
        HttpServer s = start(ex -> {
            ex.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
            ex.sendResponseHeaders(200, 0);
            List<String> payloads = new ArrayList<>();
            payloads.add(frame(null, "assistant", null, false).toString());
            payloads.add(frame(fragments.get(0), null, null, false).toString());
            payloads.add(frame(fragments.get(1), null, null, false).toString());
            payloads.add(frame(null, null, "stop", false).toString());
            writeSse(ex.getResponseBody(), payloads);
            ex.getResponseBody().write("data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8));
            ex.close();
        });
        JsonNode node = streamClient(config("http://127.0.0.1:" + s.getAddress().getPort()))
                .completeStream("POLICY", "问题", 512, context(), tokens::add);

        assertThat(tokens).containsExactly("第一步", "\n第二步");
        assertThat(node.size()).isEqualTo(6);
        assertThat(node.path("replyType").asText()).isEqualTo("ANSWER");
        assertThat(node.path("answerText").asText()).isEqualTo("第一步\n第二步");
        assertThat(node.path("usedVersionIds").get(0).asText()).isEqualTo("V1");
    }

    @Test
    void authFailureColdStatusThrowsAuthFailed() throws Exception {
        HttpServer s = start(ex -> {
            ex.sendResponseHeaders(401, 0);
            ex.close();
        });
        List<String> tokens = new ArrayList<>();
        DependencyFailure failure = catchThrowableOfType(() ->
                streamClient(config("http://127.0.0.1:" + s.getAddress().getPort()))
                        .completeStream("POLICY", "问题", 512, context(), tokens::add), DependencyFailure.class);
        assertThat(failure.result(List.of()).status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(failure.result(List.of()).errorClass()).isEqualTo("AUTH_FAILED");
        assertThat(tokens).isEmpty();
    }

    @Test
    void serverErrorColdStatusThrowsUnavailable() throws Exception {
        HttpServer s = start(ex -> {
            ex.sendResponseHeaders(500, 0);
            ex.close();
        });
        DependencyFailure failure = catchThrowableOfType(() ->
                streamClient(config("http://127.0.0.1:" + s.getAddress().getPort()))
                        .completeStream("POLICY", "问题", 512, context(), tokens -> { }), DependencyFailure.class);
        assertThat(failure.result(List.of()).status()).isEqualTo(RagStatus.UNAVAILABLE);
        assertThat(failure.result(List.of()).errorClass()).isEqualTo("UNAVAILABLE");
        assertThat(failure.result(List.of()).retryableFailure()).isTrue();
    }

    @Test
    void headerTimeoutThrowsRetryableTimeout() throws Exception {
        HttpServer s = start(ex -> {
            Thread.sleep(800);
            ex.sendResponseHeaders(200, 0);
            ex.close();
        });
        ConsultationProperties properties = config("http://127.0.0.1:" + s.getAddress().getPort());
        properties.getAi().setRequestTimeoutMs(200);
        DependencyFailure failure = catchThrowableOfType(() ->
                streamClient(properties).completeStream("POLICY", "问题", 512, context(), token -> { }),
                DependencyFailure.class);
        assertThat(failure.result(List.of()).status()).isEqualTo(RagStatus.TIMEOUT);
        assertThat(failure.result(List.of()).errorClass()).isEqualTo("TIMEOUT");
        assertThat(failure.result(List.of()).retryableFailure()).isTrue();
    }

    @Test
    void malformedFrameThrowsInvalidResponse() throws Exception {
        HttpServer s = start(ex -> {
            ex.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
            ex.sendResponseHeaders(200, 0);
            writeSse(ex.getResponseBody(), List.of("{not-json"));
            ex.close();
        });
        DependencyFailure failure = catchThrowableOfType(() ->
                streamClient(config("http://127.0.0.1:" + s.getAddress().getPort()))
                        .completeStream("POLICY", "问题", 512, context(), token -> { }), DependencyFailure.class);
        assertThat(failure.result(List.of()).status()).isEqualTo(RagStatus.INVALID_RESPONSE);
        assertThat(failure.result(List.of()).errorClass()).isEqualTo("INVALID_RESPONSE");
    }

    @Test
    void missingDoneFrameThrowsInvalidResponse() throws Exception {
        String full = sixKeyAnswerJson();
        HttpServer s = start(ex -> {
            ex.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
            ex.sendResponseHeaders(200, 0);
            List<String> payloads = new ArrayList<>();
            payloads.add(frame(full, "assistant", null, false).toString());
            payloads.add(frame(null, null, "stop", false).toString());
            writeSse(ex.getResponseBody(), payloads);
            ex.getResponseBody().close();
        });
        DependencyFailure failure = catchThrowableOfType(() ->
                streamClient(config("http://127.0.0.1:" + s.getAddress().getPort()))
                        .completeStream("POLICY", "问题", 512, context(), token -> { }), DependencyFailure.class);
        assertThat(failure.result(List.of()).status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }

    @Test
    void toolCallDeltaIsRejectedAsInvalidResponse() throws Exception {
        String full = sixKeyAnswerJson();
        HttpServer s = start(ex -> {
            ex.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
            ex.sendResponseHeaders(200, 0);
            List<String> payloads = new ArrayList<>();
            payloads.add(frame(full, "assistant", null, true).toString());
            payloads.add(frame(null, null, "stop", false).toString());
            writeSse(ex.getResponseBody(), payloads);
            ex.getResponseBody().write("data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8));
            ex.getResponseBody().close();
        });
        DependencyFailure failure = catchThrowableOfType(() ->
                streamClient(config("http://127.0.0.1:" + s.getAddress().getPort()))
                        .completeStream("POLICY", "问题", 512, context(), token -> { }), DependencyFailure.class);
        assertThat(failure.result(List.of()).status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }

    @Test
    void nullFinishReasonAtDoneThrowsInvalidResponse() throws Exception {
        String full = sixKeyAnswerJson();
        HttpServer s = start(ex -> {
            ex.getResponseHeaders().add("Content-Type", "text/event-stream; charset=utf-8");
            ex.sendResponseHeaders(200, 0);
            writeSse(ex.getResponseBody(), List.of(
                    frame(full, "assistant", null, false).toString()));
            ex.getResponseBody().write("data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8));
            ex.getResponseBody().close();
        });
        DependencyFailure failure = catchThrowableOfType(() ->
                streamClient(config("http://127.0.0.1:" + s.getAddress().getPort()))
                        .completeStream("POLICY", "问题", 512, context(), token -> { }), DependencyFailure.class);
        assertThat(failure.result(List.of()).status()).isEqualTo(RagStatus.INVALID_RESPONSE);
    }
}
