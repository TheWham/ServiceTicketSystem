package com.itticket.ai.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.ai.config.AiProperties;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/**
 * 对话大模型客户端(OpenAI 兼容 /chat/completions,DeepSeek/千问等均可接入)。
 * 未配置 api-key 时 isEnabled()=false,调用方走降级逻辑(不抛错,保证业务流程可演示)。
 */
@Slf4j
@Component
public class LlmClient {

    private final AiProperties properties;
    private final ObjectMapper objectMapper;
    private final RestClient restClient;

    public LlmClient(AiProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(60000);   // 大模型生成较慢,读超时放宽到 60s
        this.restClient = RestClient.builder().requestFactory(factory).build();
    }

    /** 是否已配置可用 */
    public boolean isEnabled() {
        String key = properties.getChat().getApiKey();
        return key != null && !key.isBlank();
    }

    /**
     * 单轮问答
     * @param systemPrompt 角色设定 + RAG 资料
     * @param userPrompt   员工问题
     * @return 模型回复文本
     */
    public String chat(String systemPrompt, String userPrompt) {
        Map<String, Object> body = Map.of(
                "model", properties.getChat().getModel(),
                "temperature", 0.3,           // 解答类问题压低随机性,防编造
                "max_tokens", 1024,
                "messages", List.of(
                        Map.of("role", "system", "content", systemPrompt),
                        Map.of("role", "user", "content", userPrompt)));

        try {
            String response = restClient.post()
                    .uri(properties.getChat().getUrl())
                    .header("Authorization", "Bearer " + properties.getChat().getApiKey())
                    .contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                    .body(objectMapper.writeValueAsString(body))
                    .retrieve()
                    .body(String.class);

            JsonNode root = objectMapper.readTree(response);
            String content = root.path("choices").path(0).path("message").path("content").asText();
            if (content.isBlank()) {
                throw new BizException(ErrorCode.SYSTEM_ERROR, "AI 返回内容为空");
            }
            return content;
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("[AI] 大模型调用失败: {}", e.getMessage());
            throw new BizException(ErrorCode.SYSTEM_ERROR, "AI 服务暂不可用，请稍后重试或直接转人工");
        }
    }
}
