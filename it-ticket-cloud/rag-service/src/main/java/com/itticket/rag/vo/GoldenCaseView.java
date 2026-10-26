package com.itticket.rag.vo;

import java.time.LocalDateTime;
import java.util.List;

/** 黄金条目视图。JSON 列已解析为列表。 */
public record GoldenCaseView(
        Long id,
        String naturalKey,
        String category,
        String difficulty,
        String query,
        String groundTruthAnswer,
        List<String> referenceChunkIds,
        List<String> expectedKeywords,
        boolean isConflictCheck,
        boolean isAdversarial,
        String sourceType,
        String sourceAiMessageId,
        boolean enabled,
        String createdBy,
        LocalDateTime createdAt) {

    public GoldenCaseView {
        referenceChunkIds = referenceChunkIds == null ? List.of() : List.copyOf(referenceChunkIds);
        expectedKeywords = expectedKeywords == null ? List.of() : List.copyOf(expectedKeywords);
    }
}
