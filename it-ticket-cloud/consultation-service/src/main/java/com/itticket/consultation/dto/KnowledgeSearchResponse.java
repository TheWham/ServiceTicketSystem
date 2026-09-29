package com.itticket.consultation.dto;

import java.util.List;

/** AI-003 / AI-004.4。 */
public record KnowledgeSearchResponse(
        List<KnowledgeSearchItem> items,
        int page,
        int pageSize,
        long total) {
}
