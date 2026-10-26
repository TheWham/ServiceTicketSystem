package com.itticket.rag.dto;

import jakarta.validation.constraints.NotBlank;

/** 黄金条目新增/编辑请求。编辑时 id 必填;新增时 naturalKey 由服务端生成。 */
public record GoldenCaseUpsertRequest(
        Long id,
        String category,
        String difficulty,
        @NotBlank(message = "query 必填") String query,
        @NotBlank(message = "groundTruthAnswer 必填") String groundTruthAnswer,
        String referenceChunkIds,
        String expectedKeywords,
        Boolean isConflictCheck,
        Boolean isAdversarial,
        String reviewNote) {
}
