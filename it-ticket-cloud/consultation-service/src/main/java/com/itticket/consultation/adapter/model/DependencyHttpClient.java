package com.itticket.consultation.adapter.model;
import com.fasterxml.jackson.databind.*;
import com.itticket.consultation.adapter.*;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
/** Shared bounded JSON transport. No redirects, body logging or implicit retries. */
public final class DependencyHttpClient {
    // 必须显式 HTTP/1.1：JDK 默认优先 HTTP/2，对明文 http:// 会先做 h2c Upgrade 协商；
    // 下游多为 uvicorn/FastAPI（不支持 h2c），协商失败时请求体被静默丢弃、只回 400 空 body，
    // 表现为 PERMANENT_HTTP 依赖降级。同因修复见 rag-service PythonRetrievalClient。
    private final HttpClient http = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NEVER).build();
    private final ObjectMapper json = new ObjectMapper();

    public JsonNode post(URI uri, JsonNode body, Map<String, String> headers,
                         RagCallContext context, long maximumMillis) {
        HttpRequest request = requestBuilder(uri, headers, context, maximumMillis)
                .POST(HttpRequest.BodyPublishers.ofString(body.toString(), StandardCharsets.UTF_8)).build();
        return exchange(request, context, maximumMillis);
    }

    public record SseFrame(String event, String data) {}

    /**
     * 帧式流式 POST：消费下游 Server-Sent Events，按完整帧回调 event/data。
     * 用于 Python agent_service 的 /chat/stream（其帧协议由 event 名区分）。
     */
    public void postSseFrames(URI uri, JsonNode body, Map<String, String> headers,
                              RagCallContext context, long maximumMillis,
                              java.util.function.Consumer<SseFrame> onFrame) {
        HttpRequest request = requestBuilder(uri, headers, context, maximumMillis)
                .header("Accept", "text/event-stream")
                .POST(HttpRequest.BodyPublishers.ofString(body.toString(), StandardCharsets.UTF_8)).build();
        try {
            HttpResponse<java.io.InputStream> response = http.send(request,
                    HttpResponse.BodyHandlers.ofInputStream());
            int status = response.statusCode();
            if (status != 200) {
                throw coldStatus(status, null);
            }
            try (java.io.BufferedReader reader = new java.io.BufferedReader(
                    new java.io.InputStreamReader(response.body(), StandardCharsets.UTF_8))) {
                String line;
                String currentEvent = null;
                StringBuilder currentData = new StringBuilder();
                while ((line = reader.readLine()) != null) {
                    context.timeoutMillis(maximumMillis);
                    if (line.startsWith("event:")) {
                        currentEvent = line.substring("event:".length()).trim();
                    } else if (line.startsWith("data:")) {
                        if (currentData.length() > 0) currentData.append("\n");
                        currentData.append(line.substring("data:".length()).trim());
                    } else if (line.isEmpty()) {
                        if (currentEvent != null && currentData.length() > 0) {
                            onFrame.accept(new SseFrame(currentEvent, currentData.toString()));
                        }
                        currentEvent = null;
                        currentData.setLength(0);
                    }
                }
            }
        } catch (DependencyFailure df) {
            throw df;
        } catch (HttpTimeoutException timeout) {
            throw new DependencyFailure(RagStatus.TIMEOUT, "TIMEOUT", true);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "INTERRUPTED", false);
        } catch (java.io.IOException unavailable) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "STREAM_FAILED", true, unavailable.getMessage());
        } catch (IllegalArgumentException invalidConfiguration) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "INVALID_CONFIGURATION", false);
        }
    }

    /**
     * 与 {@link #post} 同语义的流式 POST:响应体按 SSE 行逐行交给 lineSink(行内状态由调用方维护),
     * 计入统一超时预算(每行消费前校验,排队或分段等待中到期即真实 TIMEOUT)。
     * 冷状态码(认证/限流/5xx/其他 4xx)在首字节前判定,错误分类与 post 完全一致,无新枚举;
     * 错误响应体的前几行作为真实原因随 PERMANENT_HTTP/拒绝理由携带,不静默丢弃。
     */
    public void postStream(URI uri, JsonNode body, Map<String, String> headers,
                           RagCallContext context, long maximumMillis,
                           java.util.function.Consumer<String> lineSink) {
        HttpRequest request = requestBuilder(uri, headers, context, maximumMillis)
                .POST(HttpRequest.BodyPublishers.ofString(body.toString(), StandardCharsets.UTF_8)).build();
        try {
            HttpResponse<java.util.stream.Stream<String>> response =
                    http.send(request, HttpResponse.BodyHandlers.ofLines());
            if (response.statusCode() != 200) {
                String detail = response.body().limit(8)
                        .collect(java.util.stream.Collectors.joining("\n"));
                throw coldStatus(response.statusCode(), detail);
            }
            try (java.util.stream.Stream<String> lines = response.body()) {
                lines.forEach(line -> {
                    context.timeoutMillis(maximumMillis);
                    lineSink.accept(line);
                });
            }
        } catch (HttpTimeoutException timeout) {
            throw new DependencyFailure(RagStatus.TIMEOUT, "TIMEOUT", true);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "INTERRUPTED", false);
        } catch (java.io.IOException unavailable) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "IO", true);
        } catch (IllegalArgumentException invalidConfiguration) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "INVALID_CONFIGURATION", false);
        }
    }

    /** 只读 GET(查工单等内部只读接口)。响应格式与错误语义同 {@link #post}。 */
    public JsonNode get(URI uri, Map<String, String> headers,
                        RagCallContext context, long maximumMillis) {
        HttpRequest request = requestBuilder(uri, headers, context, maximumMillis).GET().build();
        return exchange(request, context, maximumMillis);
    }

    /** 冷状态码分类与 post/postStream 共享:鉴权/限流/5xx/永久 4xx,真实原因随详情携带。 */
    private DependencyFailure coldStatus(int status, String detail) {
        // 4xx 的真实原因在响应体里（如「分类不存在」「分类不能为空」）——
        // 只抛 errorClass 的话，前端只能看到一句 internal error，用户无从修正。
        if (status == 401 || status == 403)
            return new DependencyFailure(RagStatus.UNAVAILABLE, "AUTH_FAILED", false);
        if (status == 429) return new DependencyFailure(RagStatus.UNAVAILABLE, "RATE_LIMITED", true);
        if (status >= 500) return new DependencyFailure(RagStatus.UNAVAILABLE, "UNAVAILABLE", true);
        return new DependencyFailure(RagStatus.UNAVAILABLE, "PERMANENT_HTTP", false, detail);
    }

    private HttpRequest.Builder requestBuilder(URI uri, Map<String, String> headers,
                                               RagCallContext context, long maximumMillis) {
        HttpRequest.Builder request = HttpRequest.newBuilder(uri)
                .timeout(Duration.ofMillis(context.timeoutMillis(maximumMillis)))
                .header("Content-Type", "application/json; charset=utf-8")
                .header("X-Request-Id", context.requestId() == null ? "" : context.requestId());
        headers.forEach(request::header);
        return request;
    }

    private JsonNode exchange(HttpRequest request, RagCallContext context, long maximumMillis) {
        try {
            HttpResponse<String> response = http.send(request,
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            int status = response.statusCode();
            if (status != 200) {
                throw coldStatus(status, response.body() == null ? null : response.body());
            }
            JsonNode root;
            try {
                root = json.readTree(response.body());
            } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) {
                throw DependencyFailure.invalid();
            }
            if (root == null || !root.isObject()) throw DependencyFailure.invalid();
            context.timeoutMillis(maximumMillis);
            return root;
        } catch (HttpTimeoutException timeout) {
            throw new DependencyFailure(RagStatus.TIMEOUT, "TIMEOUT", true);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "INTERRUPTED", false);
        } catch (java.io.IOException unavailable) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "IO", true);
        } catch (IllegalArgumentException invalidConfiguration) {
            throw new DependencyFailure(RagStatus.UNAVAILABLE, "INVALID_CONFIGURATION", false);
        }
    }
}
