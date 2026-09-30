package com.itticket.consultation.adapter.generation;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
import com.itticket.consultation.enums.*;
import java.util.List;
/** Extractive answer confidence estimates evidence relevance, not a model probability. */
public final class LocalKnowledgeAnswerGenerator implements AnswerGenerator {
    @Override public GenerationResult generate(RagQuery query, List<RetrievedKnowledge> material, RagCallContext context) {
        context.timeoutMillis(Long.MAX_VALUE);
        if (material.isEmpty()) return new GenerationResult(AiReplyType.REFUSE, null, List.of(),
                RagResult.ZERO_CONFIDENCE, AiRefusalReason.NO_RELIABLE_KNOWLEDGE, "local-extractive");
        RetrievedKnowledge top = material.get(0);
        return new GenerationResult(AiReplyType.ANSWER, top.content(), List.of(top.versionId()),
                top.score(), null, "local-extractive");
    }
}
