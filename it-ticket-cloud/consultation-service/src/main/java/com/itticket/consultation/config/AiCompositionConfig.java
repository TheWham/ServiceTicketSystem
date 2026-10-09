package com.itticket.consultation.config;
import com.itticket.consultation.adapter.*;
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
    @Bean public AnswerGenerator answerGenerator(ConsultationProperties properties, OpenAiCompatibleModelClient model) {
        return switch (properties.getAi().getProvider()) {
            case "local" -> new LocalKnowledgeAnswerGenerator();
            case "openai-compatible" -> new OpenAiCompatibleAnswerGenerator(model, properties);
            default -> throw new IllegalArgumentException("Unsupported AI provider");
        };
    }
    @Bean public RetrievalPolicy retrievalPolicy(KnowledgeQueryService knowledge) { return new RetrievalPolicy(knowledge); }
    @Bean public RagAdapter ragAdapter(OfficeDomainClassifier classifier, KnowledgeRetriever retriever,
            RetrievalPolicy policy, AnswerGenerator generator) {
        return new ComposedRagAdapter(classifier, retriever, policy, generator);
    }
}
