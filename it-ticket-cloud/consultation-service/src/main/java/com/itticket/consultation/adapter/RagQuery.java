package com.itticket.consultation.adapter;

import java.util.List;
import java.util.Objects;

/** Immutable authenticated context and bounded conversation history. */
public record RagQuery(String sessionId, String question, List<Turn> priorTurns,
                       String categoryId, String assetId, int topK, RagCaller caller) {
    public RagQuery {
        Objects.requireNonNull(caller, "caller");
        priorTurns = priorTurns == null ? List.of() : List.copyOf(priorTurns);
    }

    public RagQuery(String sessionId, String question,
                    String categoryId, String assetId, int topK, RagCaller caller) {
        this(sessionId, question, List.of(), categoryId, assetId, topK, caller);
    }

    /** Persisted conversation data; history can never introduce a system role. */
    public record Turn(String role, String content) {
        public Turn {
            if (!"user".equals(role) && !"assistant".equals(role)) {
                throw new IllegalArgumentException("History role must be user or assistant");
            }
        }
    }
}
