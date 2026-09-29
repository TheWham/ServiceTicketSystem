package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.dto.AiFeedbackRequest;
import com.itticket.consultation.dto.AiFeedbackResponse;
import com.itticket.consultation.dto.TransferRequest;
import com.itticket.consultation.dto.TransferResponse;
import com.itticket.consultation.service.AiConsultationService;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.ConsultationService;
import com.itticket.consultation.service.CurrentUser;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 智能客服与转人工接口(AI-005 的 AI-API-002 / 003 / 004)。
 *
 * <p>三个接口都必须携带 {@code Idempotency-Key} 和 {@code X-Request-Id}(AI-002)。
 * 转人工不接受员工指定工程师(AI-API-004),分配由服务端按 PRD 12.1 算法决定。
 */
@Validated
@RestController
@RequestMapping("/api/v1/consultations")
@RequiredArgsConstructor
public class AiConsultationController {

    private final AiConsultationService aiConsultationService;
    private final ConsultationService consultationService;
    private final AuthzService authzService;

    /** AI-API-002:发送 AI 消息,仅使用已发布知识。 */
    @PostMapping("/{id}/ai-messages")
    public ApiEnvelope<AiChatResponse> chat(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody AiChatRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(aiConsultationService.chat(user, id, request, idempotencyKey));
    }

    /** AI-API-003:AI 回答反馈。无帮助与内容错误进入知识优化队列。 */
    @PostMapping("/{id}/feedback")
    public ApiEnvelope<AiFeedbackResponse> feedback(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody AiFeedbackRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(aiConsultationService.feedback(user, id, request, idempotencyKey));
    }

    /** AI-API-004:转人工,幂等触发自动分配。 */
    @PostMapping("/{id}/transfer")
    public ApiEnvelope<TransferResponse> transfer(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody TransferRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.transfer(user, id, request, idempotencyKey));
    }

    private static <T> ApiEnvelope<T> ok(T data) {
        return ApiEnvelope.ok(data, RequestContext.get());
    }
}
