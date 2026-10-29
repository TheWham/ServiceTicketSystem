package com.itticket.consultation.dto;

import jakarta.validation.constraints.NotBlank;

/**
 * 拒答案例处置请求。
 *
 * <p>decision 值域:GOLDEN_QA(补知识后进黄金集正常区) / GOLDEN_REFUSAL(进黄金对抗区,
 * is_adversarial 由服务端强制 true) / DISCARD(不进评测)。GOLDEN_* 时 goldenQuery /
 * goldenAnswer 缺省回落提问原文与期望拒答话术。</p>
 */
public record ReviewRequest(
        @NotBlank(message = "decision 必填") String decision,
        String reviewNote,
        String goldenQuery,
        String goldenAnswer,
        String category,
        String difficulty,
        String expectedKeywords) {
}
