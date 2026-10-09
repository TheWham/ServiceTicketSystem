package com.itticket.consultation.adapter.retrieval;
import java.math.BigDecimal;
/** Null score is a legitimate BM25-only hit, never an attributable source. */
public record RetrievedKnowledge(String chunkId, String articleId, String versionId,
        String title, String snippet, String content, String categoryId,
        BigDecimal score, String indexVersion) { }
