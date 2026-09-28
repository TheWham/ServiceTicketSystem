package com.itticket.ai.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * AI 大模型与 RAG 配置(prefix=ai,见 application.yml)。
 * chat 与 embedding 相互独立,均可为空(空 = 对应能力降级而非启动失败)。
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "ai")
public class AiProperties {

    /** 对话大模型(OpenAI 兼容接口) */
    private final Chat chat = new Chat();
    /** 向量模型(OpenAI 兼容接口) */
    private final Embedding embedding = new Embedding();
    /** RAG 检索参数 */
    private final Rag rag = new Rag();
    /** 知识回流任务参数 */
    private final Sync sync = new Sync();

    @Data
    public static class Chat {
        private String apiKey;
        private String url;
        private String model;
    }

    @Data
    public static class Embedding {
        private String apiKey;
        private String url;
        private String model;
    }

    @Data
    public static class Rag {
        /** 检索返回的最大知识条数 */
        private int topK = 5;
        /** 余弦相似度阈值,低于此值视为知识库未覆盖 */
        private double minScore = 0.55;
        /** 知识切片长度(字) */
        private int chunkSize = 500;
        /** 切片重叠长度(字) */
        private int chunkOverlap = 50;
    }

    @Data
    public static class Sync {
        private boolean enabled = true;
        private long fixedDelayMs = 600000;
        private long initialDelayMs = 60000;
    }
}
