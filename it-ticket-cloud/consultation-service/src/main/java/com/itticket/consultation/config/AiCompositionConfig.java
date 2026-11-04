package com.itticket.consultation.config;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.adapter.agent.PythonAgentClient;
import com.itticket.consultation.adapter.cache.SemanticAnswerCache;
import com.itticket.consultation.adapter.embedding.OpenAiCompatibleEmbeddingClient;
import com.itticket.consultation.adapter.generation.*;
import com.itticket.consultation.adapter.model.*;
import com.itticket.consultation.adapter.policy.*;
import com.itticket.consultation.adapter.retrieval.*;
import com.itticket.consultation.service.KnowledgeQueryService;
import org.springframework.context.annotation.*;
/** All strategy selection occurs here, fail-fast on unknown deployment values. */
@Configuration(proxyBeanMethods = false)
public class AiCompositionConfig {
    @Bean public DependencyHttpClient dependencyHttpClient() { return new DependencyHttpClient(); }
    @Bean public KnowledgeRetriever knowledgeRetriever(ConsultationProperties properties,
            KnowledgeQueryService knowledge, DependencyHttpClient http) {
        return switch (properties.getAi().getRetrievalProvider()) {
            case "local" -> new MySqlKnowledgeRetriever(knowledge, properties);
            case "rag-service" -> new RagServiceKnowledgeRetriever(properties, http);
            default -> throw new IllegalArgumentException("Unsupported AI retrieval provider");
        };
    }
    @Bean public OpenAiCompatibleModelClient modelClient(ConsultationProperties properties, DependencyHttpClient http) {
        return new OpenAiCompatibleModelClient(properties, http);
    }
    @Bean public RequestClassifier requestClassifier(ConsultationProperties properties,
            OpenAiCompatibleModelClient model) {
        return switch (properties.getAi().getProvider()) {
            case "local" -> new KeywordRequestClassifier();
            case "openai-compatible" -> new SemanticRequestClassifier(model);
            default -> throw new IllegalArgumentException("Unsupported AI provider");
        };
    }
    @Bean public RetrievalPolicy retrievalPolicy(ConsultationProperties properties,
            KnowledgeQueryService knowledge) {
        return new RetrievalPolicy(knowledge, properties.getAi().getGraphExpansion().getEdgeWhitelist(),
                properties.getAi().getGraphExpansion().getScoreFloor(),
                properties.getAi().getGraphExpansion().getMaxNeighbors());
    }

    // ---- Function Calling 智能体:生成侧下沉 Python agent_service(tools.* 已启用时生效)----
    @Bean public PythonAgentClient pythonAgentClient(ConsultationProperties properties, DependencyHttpClient http) {
        return new PythonAgentClient(properties, http);
    }
    /** 工单内部接口客户端:仅用于员工确认建单后回写工单(工单是 ticket-service 事实源)。 */
    @Bean public TicketServiceClient ticketServiceClient(ConsultationProperties properties, DependencyHttpClient http) {
        return new TicketServiceClient(properties, http);
    }

    @Bean public AnswerGenerator answerGenerator(ConsultationProperties properties, OpenAiCompatibleModelClient model,
            PythonAgentClient pythonAgentClient) {
        return switch (properties.getAi().getProvider()) {
            case "local" -> new LocalKnowledgeAnswerGenerator();
            case "openai-compatible" -> new OpenAiCompatibleAnswerGenerator(model, properties, pythonAgentClient);
            default -> throw new IllegalArgumentException("Unsupported AI provider");
        };
    }
    /**
     * 语义答案缓存(默认关闭)。开启时对嵌入模型/阈值/基址做装配期 fail-fast,
     * 版本哨兵复用本地 MySQL 锁定读(isPublishedCurrentVersion)逐条复核命中条目。
     */
    @Bean public SemanticAnswerCache semanticAnswerCache(ConsultationProperties properties,
            DependencyHttpClient http, KnowledgeQueryService knowledge) {
        ConsultationProperties.Ai.Cache cacheProperties = properties.getAi().getCache();
        if (!cacheProperties.isEnabled()) {
            return SemanticAnswerCache.disabled();
        }
        String model = cacheProperties.getEmbeddingModel();
        if (model == null || model.isBlank()) {
            throw new IllegalArgumentException(
                    "itticket.consultation.ai.cache.enabled=true 需要配置 itticket.consultation.ai.cache.embedding-model");
        }
        if (cacheProperties.getThreshold() < 0.90 || cacheProperties.getThreshold() > 1.0) {
            throw new IllegalArgumentException(
                    "语义缓存阈值必须在 [0.90,1.0] 内: itticket.consultation.ai.cache.threshold");
        }
        String baseUrl = cacheProperties.getEmbeddingBaseUrl() != null && !cacheProperties.getEmbeddingBaseUrl().isBlank()
                ? cacheProperties.getEmbeddingBaseUrl()
                : properties.getAi().getBaseUrl();
        if (baseUrl == null || baseUrl.isBlank()) {
            throw new IllegalArgumentException(
                    "语义缓存需要嵌入端点: itticket.consultation.ai.cache.embedding-base-url 或 itticket.consultation.ai.base-url");
        }
        OpenAiCompatibleEmbeddingClient embeddings = new OpenAiCompatibleEmbeddingClient(
                baseUrl, model, properties.getAi().getApiKey(), cacheProperties.getEmbeddingTimeoutMs(), http);
        return new SemanticAnswerCache(cacheProperties, embeddings,
                knowledge::isPublishedCurrentVersion, java.time.Clock.systemUTC());
    }
    @Bean public RagAdapter ragAdapter(RequestClassifier classifier, KnowledgeRetriever retriever,
            RetrievalPolicy policy, AnswerGenerator generator, PythonAgentClient pythonAgentClient,
            SemanticAnswerCache semanticAnswerCache) {
        // 工具意图的放行只在 Function Calling 开启时生效：agent 关了就不消费判定结果里的 tool，
        // 避免越过拒答后得到一段无依据作答（那是放宽拒答策略，不是本意）。
        return new ComposedRagAdapter(classifier, retriever, policy, generator, pythonAgentClient.enabled(),
                semanticAnswerCache);
    }
}