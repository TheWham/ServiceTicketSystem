package com.itticket.rag.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * ============================================================================
 * Dify 知识库接入配置属性类 (DifyProperties)
 * ============================================================================
 *
 * 用于映射 application.yml 中 rag.dify 配置项：
 * - enabled: 是否启用 Dify 知识库通道（默认 false，未启用时相关端点直接拒绝）
 * - base-url: Dify Dataset API 基础地址（默认 http://120.92.138.195/v1）
 * - api-key: 知识库 API 密钥 —— 一律由环境变量 DIFY_API_KEY 注入，不提供默认值
 * - dataset-id: 目标知识库 ID；留空时按 dataset-name 自动创建空知识库并复用
 * - indexing-technique: 索引技术（high_quality / economy，默认 high_quality）
 * - search-method: 默认检索方式（hybrid_search / semantic_search / full_text_search）
 * - timeout-seconds: HTTP 调用超时（秒）
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Component
@ConfigurationProperties(prefix = "rag.dify")
public class DifyProperties {

    /** 是否启用 Dify 知识库通道 */
    private boolean enabled = false;

    /** Dify Dataset API 基础地址 */
    private String baseUrl = "http://120.92.138.195:18086/v1";

    /** 知识库 API 密钥（Bearer），由 DIFY_API_KEY 环境变量注入，禁止明文入库/入 Git/入日志 */
    private String apiKey;

    /** 目标知识库 ID；留空时自动按 dataset-name 创建并复用 */
    private String datasetId;

    /** 自动创建知识库时使用的名称 */
    private String datasetName = "it-ticket-knowledge";

    /**
     * 文档表单模式，必须与目标知识库的 doc_form 一致，否则创建文档返回 400
     * （text_model / hierarchical_model / qa_model）。
     */
    private String docForm = "hierarchical_model";

    /** 索引技术：high_quality（向量+关键词混合索引）或 economy（仅关键词） */
    private String indexingTechnique = "high_quality";

    /** 默认检索方式：hybrid_search / semantic_search / full_text_search */
    private String searchMethod = "hybrid_search";

    /** 默认召回条数 */
    private Integer topK = 5;

    /** 默认相关性分数阈值（0~1），低于阈值的分段被过滤 */
    private Double scoreThreshold = 0.3;

    /** HTTP 调用超时（秒）；上传与状态轮询共用 */
    private Integer timeoutSeconds = 30;
}
