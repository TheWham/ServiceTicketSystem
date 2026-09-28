package com.itticket.rag.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * ============================================================================
 * RAG 向量模型配置属性类 (EmbeddingProperties)
 * ============================================================================
 *
 * 用于映射 application.yml 中 rag.embedding 配置项：
 * - base-url: OpenAI 兼容接口 Base URL
 * - api-key: 访问认证 Token
 * - model: 向量模型名称（默认 qwen3.7-text-embedding）
 * - dimensions: 向量维度（默认 1024）
 * - batch-size: 批处理大小（默认 16）
 * - timeout-seconds: 超时时间（秒）
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Component
@ConfigurationProperties(prefix = "rag.embedding")
public class EmbeddingProperties {

    /** OpenAI 兼容接口的基础端点 */
    private String baseUrl = "https://ws-klculckg6dog3won.cn-beijing.maas.aliyuncs.com/compatible-mode/v1";

    /** 访问密钥 API Key */
    private String apiKey = "sk-ws-H.PLYPHLE.Zvdn.MEUCIQDAkPAHsTzjr_yE5FKXbFSED0EYkPnWuBOhl4YIc1PfkAIgU9F0mF9nYISNFHRb3IqhmAuUkzu-sgB_S3sH2S2TxkM";

    /** 向量嵌入模型标识 */
    private String model = "qwen3.7-text-embedding";

    /** 向量空间维度 */
    private Integer dimensions = 1024;

    /** 单次调用批处理最大文本块数 */
    private Integer batchSize = 16;

    /** 请求超时时间（秒） */
    private Integer timeoutSeconds = 15;
}
