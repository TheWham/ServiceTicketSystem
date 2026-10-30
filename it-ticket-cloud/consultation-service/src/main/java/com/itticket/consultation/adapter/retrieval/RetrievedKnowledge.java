package com.itticket.consultation.adapter.retrieval;
import com.fasterxml.jackson.annotation.JsonInclude;
import java.math.BigDecimal;
/** Null score is a legitimate BM25-only hit, never an attributable source. */
public record RetrievedKnowledge(String chunkId, String articleId, String versionId,
        String title, String snippet, String content, String categoryId,
        BigDecimal score, String indexVersion,
        @JsonInclude(JsonInclude.Include.NON_NULL) Boolean graphExpanded,
        @JsonInclude(JsonInclude.Include.NON_NULL) String expandedFrom,
        @JsonInclude(JsonInclude.Include.NON_NULL) String relation) { }
