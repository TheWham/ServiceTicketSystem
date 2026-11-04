package com.itticket.consultation.adapter.embedding;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.model.DependencyHttpClient;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.RagStatus;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * OpenAI 兼容 /embeddings 客户端契约:
 *  - 请求体 {"model":...,"input":[text]}, Bearer 鉴权, 复用统一超时预算(RagCallContext);
 *  - 返回向量必须 L2 归一化(余弦相似度匹配的前提);
 *  - 空 data / 缺 data / 非数字分量 / 零向量均属协议违规(INVALID_RESPONSE), 不静默;
 *  - HTTP 401/500 沿 DependencyHttpClient 既有错误分类。
 */
class OpenAiCompatibleEmbeddingClientTest {

    private final ObjectMapper json = new ObjectMapper();
    private HttpServer server;
    private DependencyHttpClient http;
    private OpenAiCompatibleEmbeddingClient client;
    private final AtomicReference<JsonNode> lastRequest = new AtomicReference<>();
    private final AtomicReference<Map<String, String>> lastHeaders = new AtomicReference<>();
    private volatile long delayMillis = 0;
    private volatile String responseBody = "{\"data\":[{\"embedding\":[3.0,4.0]}]}";
    private volatile int responseStatus = 200;

    @BeforeEach
    void start() throws Exception {
        server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/embeddings", exchange -> {
            lastRequest.set(json.readTree(exchange.getRequestBody()));
            Map<String, String> headers = new java.util.HashMap<>();
            for (String header : List.of("Authorization", "X-Request-Id"))
                headers.put(header, exchange.getRequestHeaders().getFirst(header));
            lastHeaders.set(headers);
            pause(delayMillis);
            byte[] response = responseBody.getBytes(java.nio.charset.StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(responseStatus, response.length);
            try (OutputStream out = exchange.getResponseBody()) { out.write(response); }
        });
        server.start();
        http = new DependencyHttpClient();
        client = new OpenAiCompatibleEmbeddingClient(baseUrl(), "ksp-embedding-v1", "test-token", 200, http);
    }

    @AfterEach
    void stop() { server.stop(0); }

    @Test
    void embedsAreL2NormalizedAndRequestCarriesModelInputAndAuth() {
        float[] vector = client.embed("会议没有声音", context(10_000));

        assertThat((double) vector[0]).isCloseTo(0.6, org.assertj.core.data.Offset.offset(1e-6));
        assertThat((double) vector[1]).isCloseTo(0.8, org.assertj.core.data.Offset.offset(1e-6));
        assertThat(lastRequest.get().path("model").asText()).isEqualTo("ksp-embedding-v1");
        assertThat(lastRequest.get().path("input")).isInstanceOf(com.fasterxml.jackson.databind.node.ArrayNode.class);
        assertThat(lastRequest.get().path("input").get(0).asText()).isEqualTo("会议没有声音");
        assertThat(lastHeaders.get()).containsEntry("Authorization", "Bearer test-token");
        assertThat(lastHeaders.get().get("X-Request-Id")).isNotBlank();
    }

    @Test
    void emptyDataArrayIsInvalid() {
        responseBody = "{\"data\":[]}";
        assertThatThrownBy(() -> client.embed("q", context(10_000)))
                .isInstanceOf(DependencyFailure.class)
                .extracting(f -> ((DependencyFailure) f).result(java.util.List.of()).status())
                .isEqualTo(RagStatus.INVALID_RESPONSE);
    }

    @Test
    void missingDataIsInvalid() {
        responseBody = "{\"object\":\"list\"}";
        assertThatThrownBy(() -> client.embed("q", context(10_000)))
                .isInstanceOf(DependencyFailure.class)
                .extracting(f -> ((DependencyFailure) f).result(java.util.List.of()).status())
                .isEqualTo(RagStatus.INVALID_RESPONSE);
    }

    @Test
    void nonNumericComponentIsInvalid() {
        responseBody = "{\"data\":[{\"embedding\":[1.0,\"x\"]}]}";
        assertThatThrownBy(() -> client.embed("q", context(10_000)))
                .isInstanceOf(DependencyFailure.class);
    }

    @Test
    void zeroVectorIsInvalid() {
        responseBody = "{\"data\":[{\"embedding\":[0.0,0.0]}]}";
        assertThatThrownBy(() -> client.embed("q", context(10_000)))
                .isInstanceOf(DependencyFailure.class)
                .extracting(f -> ((DependencyFailure) f).result(java.util.List.of()).status())
                .isEqualTo(RagStatus.INVALID_RESPONSE);
    }

    @Test
    void unauthorizedMapsToAuthFailed() {
        responseStatus = 401;
        assertThatThrownBy(() -> client.embed("q", context(10_000)))
                .isInstanceOf(DependencyFailure.class)
                .extracting(f -> ((DependencyFailure) f).result(java.util.List.of()).status())
                .isEqualTo(RagStatus.UNAVAILABLE);
    }

    @Test
    void serverErrorIsUnavailable() {
        responseStatus = 500;
        assertThatThrownBy(() -> client.embed("q", context(10_000)))
                .isInstanceOf(DependencyFailure.class)
                .extracting(f -> ((DependencyFailure) f).result(java.util.List.of()).status())
                .isEqualTo(RagStatus.UNAVAILABLE);
    }

    @Test
    void timeoutMapsToTimeout() {
        delayMillis = 400;
        assertThatThrownBy(() -> client.embed("q", context(10_000)))
                .isInstanceOf(DependencyFailure.class)
                .extracting(f -> ((DependencyFailure) f).result(java.util.List.of()).status())
                .isEqualTo(RagStatus.TIMEOUT);
    }

    @Test
    void embeddingConsumesUnifiedDeadlineBudget() {
        RagCallContext expired = new RagCallContext("req-1", System.nanoTime() - 1, new RagExecutionAudit());
        assertThatThrownBy(() -> client.embed("q", expired))
                .isInstanceOf(DependencyFailure.class)
                .extracting(f -> ((DependencyFailure) f).result(java.util.List.of()).errorClass())
                .isEqualTo("TIMEOUT");
    }

    private RagCallContext context(long budgetMillis) {
        return new RagCallContext("req-1", System.nanoTime() + budgetMillis * 1_000_000L, new RagExecutionAudit());
    }

    private String baseUrl() { return "http://127.0.0.1:" + server.getAddress().getPort(); }

    private static void pause(long delay) {
        try { if (delay > 0) Thread.sleep(delay); }
        catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
    }
}
