package com.itticket.rag.dto.ai;

import jakarta.validation.constraints.Size;

/**
 * AI 消息上下文引用 —— 契约 AI-003 / AI-004.2。
 */
public record AiContextRefs(
        @Size(max = 64) String categoryId,
        @Size(max = 64) String assetId) {
}
