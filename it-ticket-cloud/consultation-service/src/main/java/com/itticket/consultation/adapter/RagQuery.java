package com.itticket.consultation.adapter;
import java.util.Objects;
/** Immutable authenticated context captured before switching threads. */
public record RagQuery(String sessionId, String question,
                       String categoryId, String assetId, int topK, RagCaller caller) {
    public RagQuery { Objects.requireNonNull(caller, "caller"); }
}
