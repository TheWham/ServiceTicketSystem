package com.itticket.consultation.adapter.generation;
import com.itticket.consultation.adapter.*;
import com.itticket.consultation.adapter.retrieval.RetrievedKnowledge;
import java.util.List;
public interface AnswerGenerator {
    GenerationResult generate(RagQuery query, List<RetrievedKnowledge> material, RagCallContext context);
}
