package com.itticket.ai.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.ai.config.AiProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Map;

/**
 * 向量模型客户端(OpenAI 兼容 /embeddings,如硅基流动 BGE-M3)。
 * 未配置 api-key 时 isEnabled()=false,知识库检索整体降级为空结果(AI 仅凭通用能力回答)。
 * 注意:embedding 模型一经使用不要中途更换,不同模型向量空间不兼容,库内向量需全部重算。
 */
@Slf4j
@Component
public class EmbeddingClient {

    private final AiProperties properties;
    private final ObjectMapper objectMapper;
    private final RestClient restClient;

    public EmbeddingClient(AiProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(30000);
        this.restClient = RestClient.builder().requestFactory(factory).build();
    }

    public boolean isEnabled() {
        String key = properties.getEmbedding().getApiKey();
        return key != null && !key.isBlank();
    }

    /**
     * 文本向量化
     * @return 向量数组;调用失败时返回 null(由调用方决定降级策略)
     */
    public float[] embed(String text) {
        Map<String, Object> body = Map.of(
                "model", properties.getEmbedding().getModel(),
                "input", text);
        try {
            String response = restClient.post()
                    .uri(properties.getEmbedding().getUrl())
                    .header("Authorization", "Bearer " + properties.getEmbedding().getApiKey())
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsString(body))
                    .retrieve()
                    .body(String.class);

            JsonNode vectorNode = objectMapper.readTree(response)
                    .path("data").path(0).path("embedding");
            if (!vectorNode.isArray() || vectorNode.isEmpty()) {
                log.warn("[AI] embedding 返回为空");
                return null;
            }
            float[] vector = new float[vectorNode.size()];
            for (int i = 0; i < vectorNode.size(); i++) {
                vector[i] = (float) vectorNode.path(i).asDouble();
            }
            return vector;
        } catch (Exception e) {
            log.error("[AI] embedding 调用失败: {}", e.getMessage());
            return null;
        }
    }
}
