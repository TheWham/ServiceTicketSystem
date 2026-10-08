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
 * 【规范引用】（路径相对仓库根目录 docs/）：
 * - MR-001 · specs/10-model-rag-integration.md:13 — Provider 配置以不可变版本发布。
 * - MR-002 · specs/10-model-rag-integration.md:40 — apiKey 只存 Secret 引用：
 *   本类不提供明文默认值，一律由环境变量 EMBEDDING_API_KEY 注入，禁止入库/入 Git/入日志。
 * - RD-006 · specs/04-resilience-degradation.md:67 — 未注入凭据时按依赖不可用降级（见 EmbeddingClientService）。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Component
@ConfigurationProperties(prefix = "rag.embedding")
public class EmbeddingProperties {

    /** OpenAI 兼容接口的基础端点 —— 一律由 EMBEDDING_BASE_URL 环境变量注入，不提供默认值 */
    private String baseUrl;

    /** 访问密钥 API Key —— 一律由环境变量 EMBEDDING_API_KEY 注入，不提供默认值（MR-002 · specs/10-model-rag-integration.md:40：禁止明文入库） */
    private String apiKey;

    /** 向量嵌入模型标识 */
    private String model = "qwen3.7-text-embedding";

    /** 向量空间维度 */
    private Integer dimensions = 1024;

    /** 单次调用批处理最大文本块数 */
    private Integer batchSize = 16;

    /** 请求超时时间（秒） */
    private Integer timeoutSeconds = 15;
}
