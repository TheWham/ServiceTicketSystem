package com.itticket.consultation.config;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.adapter.agent.PythonAgentClient;
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
    @Bean public OfficeDomainClassifier officeDomainClassifier(ConsultationProperties properties,
            OpenAiCompatibleModelClient model) {
        return switch (properties.getAi().getProvider()) {
            case "local" -> new LocalOfficeDomainClassifier();
            case "openai-compatible" -> new SemanticOfficeDomainClassifier(model);
            default -> throw new IllegalArgumentException("Unsupported AI provider");
        };
    }
    @Bean public RetrievalPolicy retrievalPolicy(KnowledgeQueryService knowledge) { return new RetrievalPolicy(knowledge); }

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
     * 工具意图识别器。仅在 Function Calling 开启时放行 —— 未开 agent 时越过拒答
     * 只会得到无依据的作答，属放宽拒答策略，不是本意（见 {@link ToolIntentDetector}）。
     */
    @Bean public ToolIntentDetector toolIntentDetector(PythonAgentClient pythonAgentClient) {
        return new ToolIntentDetector(pythonAgentClient.enabled());
    }

    @Bean public RagAdapter ragAdapter(OfficeDomainClassifier classifier, KnowledgeRetriever retriever,
            RetrievalPolicy policy, AnswerGenerator generator, ToolIntentDetector toolIntentDetector) {
        return new ComposedRagAdapter(classifier, retriever, policy, generator, toolIntentDetector);
    }
}