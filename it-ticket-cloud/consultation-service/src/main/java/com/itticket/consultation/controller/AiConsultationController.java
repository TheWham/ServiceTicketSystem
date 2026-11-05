package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.dto.AiFeedbackRequest;
import com.itticket.consultation.dto.AiFeedbackResponse;
import com.itticket.consultation.dto.TransferRequest;
import com.itticket.consultation.dto.TransferResponse;
import com.itticket.consultation.dto.TicketDraftConfirmRequest;
import com.itticket.consultation.dto.TicketDraftConfirmResponse;
import com.itticket.consultation.service.AiConsultationService;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.ConsultationService;
import com.itticket.consultation.service.CurrentUser;
import com.itticket.consultation.service.stream.AiChatStreamOrchestrator;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyEmitter;

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
    private final AiChatStreamOrchestrator aiChatStreamOrchestrator;
    private final ConsultationProperties properties;

    /** AI-API-002:发送 AI 消息（非流式，默认 Accept: application/json）。 */
    @PostMapping(value = "/{id}/ai-messages", produces = org.springframework.http.MediaType.APPLICATION_JSON_VALUE)
    public ApiEnvelope<AiChatResponse> chat(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody AiChatRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(aiConsultationService.chat(user, id, request, idempotencyKey));
    }

    /**
     * AI-API-002 流式变体(T-6):SSE 端点常在,事件 queued/token/final/error。
     * 会话内严格串行(FIFO);同 Idempotency-Key 重放由幂等服务处理。
     * final 搬与旧同步端点同一份 AiChatResponse;error 只给真实 errorClass。
     * 断连(容器回调三选一)即 close,编排器中止本流并让队列腾位。
     */
    @PostMapping("/{id}/ai-messages/stream")
    public ResponseBodyEmitter chatStream(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody AiChatRequest request) {
        CurrentUser user = authzService.currentUser();
        // 容器异步超时必须盖住整个统一预算:排队+首字节+生成(RD-003 120s)+裕量,
        // 默认 30s 会在长答案上把活跃流掐断(2026-11-05 流式评审 C2);断连由三回调兜底。
        ConsultationProperties.Ai ai = properties.getAi();
        ResponseBodyEmitter emitter = new ResponseBodyEmitter(
                ai.getRequestTimeoutMs() + ai.getFirstTokenTimeoutMs() + 30_000L);
        SseChatEventSink events = new SseChatEventSink(emitter);
        AiChatStreamOrchestrator.SseHandle handle =
                aiChatStreamOrchestrator.openStream(user, id, request, idempotencyKey, events);
        emitter.onCompletion(handle::close);
        emitter.onError(cause -> handle.close());
        emitter.onTimeout(handle::close);
        return emitter;
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

    /**
     * 人机回环第二步:员工确认 AI 建单草稿后真正建单。
     *
     * <p>AI 只产草稿(随 AI 消息回复的 ticketDraft),员工在前端确认(可编辑字段)后调本接口,
     * 由服务端经 ticket-service 建单并把咨询转为工单。AI 自身无法建单。
     */
    @PostMapping("/{id}/ticket-draft/confirm")
    public ApiEnvelope<TicketDraftConfirmResponse> confirmTicketDraft(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody TicketDraftConfirmRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.confirmTicketDraft(user, id, request, idempotencyKey));
    }

    private static <T> ApiEnvelope<T> ok(T data) {
        return ApiEnvelope.ok(data, RequestContext.get());
    }
}
