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
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NEVER).build();
    private final ObjectMapper json = new ObjectMapper();
    public JsonNode post(URI uri, JsonNode body, Map<String, String> headers,
                         RagCallContext context, long maximumMillis) {
        try {
            HttpRequest.Builder request = HttpRequest.newBuilder(uri)
                    .timeout(Duration.ofMillis(context.timeoutMillis(maximumMillis)))
                    .header("Content-Type", "application/json; charset=utf-8")
                    .header("X-Request-Id", context.requestId() == null ? "" : context.requestId());
            headers.forEach(request::header);
            HttpResponse<String> response = http.send(request.POST(
                    HttpRequest.BodyPublishers.ofString(body.toString(), StandardCharsets.UTF_8)).build(),
                    HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            int status = response.statusCode();
            if (status == 401 || status == 403)
                throw new DependencyFailure(RagStatus.UNAVAILABLE, "AUTH_FAILED", false);
            if (status == 429) throw new DependencyFailure(RagStatus.UNAVAILABLE, "RATE_LIMITED", true);
            if (status >= 500) throw new DependencyFailure(RagStatus.UNAVAILABLE, "UNAVAILABLE", true);
            if (status != 200) throw new DependencyFailure(RagStatus.UNAVAILABLE, "PERMANENT_HTTP", false);
            JsonNode root;
            try { root = json.readTree(response.body()); }
            catch (com.fasterxml.jackson.core.JsonProcessingException invalid) { throw DependencyFailure.invalid(); }
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
