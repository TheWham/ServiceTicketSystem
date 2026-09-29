package com.itticket.rag.dto.ai;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * AI 提问请求 —— 契约 AI-003 / AI-004.2（AI-API-002 请求体）。
 *
 * <p>操作者身份从认证上下文解析，不接受请求体传入的操作者 ID（AI-002）。</p>
 */
public record AiChatRequest(
        @NotBlank @Size(max = 8000) String message,
        @Valid AiContextRefs contextRefs) {
}
