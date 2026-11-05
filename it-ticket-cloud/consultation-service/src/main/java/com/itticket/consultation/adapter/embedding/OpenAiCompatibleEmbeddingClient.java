package com.itticket.consultation.adapter.embedding;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.consultation.adapter.DependencyFailure;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.model.DependencyHttpClient;

import java.net.URI;
import java.util.Map;

/**
 * OpenAI 兼容 /embeddings 客户端(与 OpenAiCompatibleModelClient 同族协议):
 * POST {base}/embeddings,body {"model":...,"input":[text]},Bearer 鉴权。
 * 响应 data[0].embedding 解析为 float[] 后 L2 归一化;空 data、缺字段、
 * 非数字分量、零范数一律 DependencyFailure.invalid()——零向量无法参与
 * 相似度比较,静默返回会让缓存把任意两问判成满分命中。
 * HTTP 状态码与网络故障分类沿用 DependencyHttpClient;调用时长上限
 * timeoutMillis 传入后由 context.timeoutMillis 与统一预算取小。
 */
public final class OpenAiCompatibleEmbeddingClient implements EmbeddingClient {

    private final String baseUrl;
    private final String model;
    private final String apiKey;
    private final long timeoutMillis;
    private final DependencyHttpClient http;
    private final ObjectMapper json = new ObjectMapper();

    public OpenAiCompatibleEmbeddingClient(String baseUrl, String model, String apiKey,
                                           long timeoutMillis, DependencyHttpClient http) {
        this.baseUrl = baseUrl;
        this.model = model;
        this.apiKey = apiKey;
        this.timeoutMillis = timeoutMillis;
        this.http = http;
    }

    @Override
    public float[] embed(String text, RagCallContext context) {
        ObjectNode body = json.createObjectNode().put("model", model);
        body.putArray("input").add(text);
        JsonNode root = http.post(URI.create(baseUrl + "/embeddings"), body,
                Map.of("Authorization", "Bearer " + apiKey), context, timeoutMillis);
        JsonNode data = root.path("data");
        if (!data.isArray() || data.isEmpty() || data.path(0).path("embedding") == null
                || !data.path(0).path("embedding").isArray()) {
            throw DependencyFailure.invalid();
        }
        JsonNode vector = data.get(0).get("embedding");
        float[] out = new float[vector.size()];
        double norm = 0.0;
        for (int i = 0; i < vector.size(); i++) {
            JsonNode component = vector.get(i);
            if (!component.isNumber()) {
                throw DependencyFailure.invalid();
            }
            out[i] = component.floatValue();
            norm += (double) out[i] * out[i];
        }
        if (out.length == 0 || norm == 0.0) {
            throw DependencyFailure.invalid();
        }
        double inv = 1.0 / Math.sqrt(norm);
        for (int i = 0; i < out.length; i++) {
            out[i] = (float) (out[i] * inv);
        }
        return out;
    }
}
