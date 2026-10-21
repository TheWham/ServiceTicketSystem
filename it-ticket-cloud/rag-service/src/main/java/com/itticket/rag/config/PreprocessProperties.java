package com.itticket.rag.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * ============================================================================
 * 文档预处理服务配置属性类 (PreprocessProperties)
 * ============================================================================
 *
 * 映射 application.yml 中 rag.preprocess 配置项，指向 doc-ingest-service
 * （Python FastAPI 文档清洗/切块预处理微服务）：
 * - base-url: 服务基址（如 http://127.0.0.1:8310）；不配置则不装配
 *   DocPreprocessClient，DOCX 上传显式拒绝（装配时选择供应商，非运行时分支）
 * - timeout-seconds: 预处理单次调用超时（docx 清洗为 CPU 密集型，默认 60s）
 */
@Data
@Component
@ConfigurationProperties(prefix = "rag.preprocess")
public class PreprocessProperties {

    /** doc-ingest-service 基址，如 http://127.0.0.1:8310 */
    private String baseUrl;

    /** 预处理单次调用超时（秒） */
    private int timeoutSeconds = 60;
}
