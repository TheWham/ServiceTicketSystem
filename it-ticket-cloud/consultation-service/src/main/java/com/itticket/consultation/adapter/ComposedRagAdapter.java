package com.itticket.consultation.adapter;
import com.itticket.consultation.adapter.generation.*;
import com.itticket.consultation.adapter.policy.*;
import com.itticket.consultation.adapter.retrieval.*;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.enums.*;
import java.math.BigDecimal;
import java.util.*;
/** The only answer orchestrator. Providers are selected in Spring assembly, never here. */
public final class ComposedRagAdapter implements RagAdapter {
    private final OfficeDomainClassifier classifier;
    private final KnowledgeRetriever retriever;
    private final RetrievalPolicy policy;
    private final AnswerGenerator generator;
    public ComposedRagAdapter(OfficeDomainClassifier classifier, KnowledgeRetriever retriever,
                              RetrievalPolicy policy, AnswerGenerator generator) {
        this.classifier = classifier; this.retriever = retriever; this.policy = policy; this.generator = generator;
    }
    @Override public RagResult answer(RagQuery query, RagCallContext context) {
        List<String> retrieved = List.of();
        try {
            RagResult domainVerdict = restrict(classifier.classify(query, context));
            if (domainVerdict != null) return domainVerdict;
            RetrievalResult result = retriever.retrieve(query, context);
            retrieved = result.items().stream().map(RetrievedKnowledge::versionId).distinct().toList();
            context.audit().recordRetrievedVersions(retrieved);
            domainVerdict = restrict(result.domain());
            if (domainVerdict != null) return domainVerdict;
            if (result.refusalReason() != null) return RagResult.refuse(result.refusalReason(), null, retrieved);
            List<RetrievedKnowledge> material = policy.material(result, context);
            if (result.reliable() && material.isEmpty())
                return RagResult.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, null, retrieved);
            context.timeoutMillis(Long.MAX_VALUE);
            GenerationResult generated = generator.generate(query, material, context);
            context.timeoutMillis(Long.MAX_VALUE);
            Map<String, RetrievedKnowledge> byVersion = new LinkedHashMap<>();
            material.forEach(item -> byVersion.put(item.versionId(), item));
            if (generated.usedVersionIds().stream().anyMatch(id -> !byVersion.containsKey(id)))
                throw DependencyFailure.invalid();
            if (generated.refusalReason() != null)
                return RagResult.refuse(generated.refusalReason(), generated.modelVersion(), retrieved);
            if (generated.replyType() == AiReplyType.REFUSE || !material.isEmpty() && generated.usedVersionIds().isEmpty())
                return RagResult.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, generated.modelVersion(), retrieved);
            List<KnowledgeCitationDto> citations = generated.usedVersionIds().stream().distinct()
                    .map(byVersion::get).map(item -> new KnowledgeCitationDto(item.articleId(), item.versionId(),
                            item.title(), item.score(), item.snippet())).toList();
            boolean general = material.isEmpty();
            String text = generated.answerText();
            if (general && text != null && !text.isBlank())
                text = "以下为通用办公 IT 建议，无知识库依据。\n\n" + text;
            if (text != null && text.length() > 12000) throw DependencyFailure.invalid();
            return new RagResult(RagStatus.SUCCESS, generated.replyType(), text, citations,
                    generated.confidence(), null, generated.modelVersion(), retrieved, 0, null, general, false);
        } catch (RetrievalPolicy.StaleKnowledge stale) {
            return RagResult.refuse(AiRefusalReason.NO_RELIABLE_KNOWLEDGE, null, retrieved);
        } catch (DependencyFailure failure) {
            return failure.result(retrieved);
        }
    }
    private static RagResult restrict(OfficeDomain domain) {
        return switch (domain) {
            case OFFICE_IT -> null;
            case OFF_TOPIC -> RagResult.refuse(AiRefusalReason.OFF_TOPIC, null, List.of());
            case HIGH_RISK -> RagResult.refuse(AiRefusalReason.HIGH_RISK_TOPIC, null, List.of());
            case UNCERTAIN -> new RagResult(RagStatus.SUCCESS, AiReplyType.CLARIFY,
                    "请补充遇到问题的办公设备或应用、具体表现及错误提示。",
                    List.of(), BigDecimal.ONE, null, null, List.of(), 0, null, false, false);
        };
    }
}
