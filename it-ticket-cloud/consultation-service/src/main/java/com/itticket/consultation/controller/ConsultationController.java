package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.PagedData;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.ConsultationCreatedResponse;
import com.itticket.consultation.dto.ConsultationProjection;
import com.itticket.consultation.dto.ConsultationResolutionRequest;
import com.itticket.consultation.dto.ContentRequest;
import com.itticket.consultation.dto.CreateConsultationRequest;
import com.itticket.consultation.dto.MessageProjection;
import com.itticket.consultation.dto.ReasonRequest;
import com.itticket.consultation.dto.QueueStatusResponse;
import com.itticket.consultation.dto.TicketDraftResponse;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.ConsultationMessageService;
import com.itticket.consultation.service.ConsultationService;
import com.itticket.consultation.service.CurrentUser;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 咨询会话接口。
 *
 * <p>路径来源:AI-005 的 AI-API-001(创建咨询)与 OpenAPI 05 的 /consultations 系列。
 * 写接口的 {@code Idempotency-Key} 与全部接口的 {@code X-Request-Id} 都是契约必填
 * (AI-002、05 的 parameters);缺失时由 {@code RequestIdFilter} 或校验层返回 VALIDATION_ERROR。
 *
 * <p>字段命名沿用各自契约:AI-005 的 DTO 是 camelCase,05 的 Schema 是 snake_case。
 * 两者不一致是契约本身的差异,实现不做统一,已在交付说明中列为待回写项。
 */
@Validated
@RestController
@RequestMapping("/api/v1/consultations")
@RequiredArgsConstructor
public class ConsultationController {

    private final ConsultationService consultationService;
    private final ConsultationMessageService messageService;
    private final AuthzService authzService;

    /** AI-API-001 创建咨询。只创建咨询,不创建工单。 */
    @PostMapping
    public ApiEnvelope<ConsultationCreatedResponse> create(
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody CreateConsultationRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.create(user, request, idempotencyKey));
    }

    /** OpenAPI 05 listConsultations。数据范围按 PRD 5.2 由服务端裁剪。 */
    @GetMapping
    public ApiEnvelope<PagedData<ConsultationProjection>> list(
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int pageSize) {
        return ok(consultationService.list(authzService.currentUser(), page, pageSize));
    }

    /** OpenAPI 05 getConsultation。 */
    @GetMapping("/{id}")
    public ApiEnvelope<ConsultationProjection> get(@PathVariable String id) {
        CurrentUser user = authzService.currentUser();
        Consultation consultation = consultationService.loadAuthorized(user, id);
        return ok(ConsultationProjection.of(consultation));
    }

    /** 员工排队状态:仅返回是否已分配及该工程师当前待首次回复人数。 */
    @GetMapping("/{id}/queue-status")
    public ApiEnvelope<QueueStatusResponse> queueStatus(@PathVariable String id) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.queueStatus(user, id));
    }

    /** OpenAPI 05 getTicketDraftFromConsultation:咨询转单预填,员工可检查修改后提交。 */
    @GetMapping("/{id}/ticket-draft")
    public ApiEnvelope<TicketDraftResponse> ticketDraft(@PathVariable String id) {
        return ok(consultationService.ticketDraft(authzService.currentUser(), id));
    }

    /** OpenAPI 05 sendHumanConsultationMessage。 */
    @PostMapping("/{id}/messages")
    public ApiEnvelope<MessageProjection> sendMessage(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody ContentRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.sendMessage(user, id, request, idempotencyKey));
    }

    /** OpenAPI 05 listConsultationMessages。仅会话参与者可读正文(PRD 5.2)。 */
    @GetMapping("/{id}/messages")
    public ApiEnvelope<PagedData<MessageProjection>> listMessages(
            @PathVariable String id,
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int pageSize) {
        CurrentUser user = authzService.currentUser();
        Consultation consultation = consultationService.loadAuthorized(user, id);
        return ok(messageService.list(user, consultation, page, pageSize));
    }

    /** OpenAPI 05 resolveConsultation。工程师提交解决结论。 */
    @PostMapping("/{id}/resolution")
    public ApiEnvelope<ConsultationProjection> submitResolution(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody ConsultationResolutionRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.submitResolution(user, id, request, idempotencyKey));
    }

    /**
     * 员工确认解决(PENDING_CONFIRMATION → RESOLVED)。
     *
     * <p>契约缺口:该迁移在 SM-CONSULT-001 中明确存在,但 OpenAPI 05 与 AI-005 都没有对应路径。
     * 这里按动作语义补 {@code POST /consultations/{id}/confirmation},需要回写 05。
     */
    @PostMapping("/{id}/confirmation")
    public ApiEnvelope<ConsultationProjection> confirm(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.confirmResolution(user, id, idempotencyKey));
    }

    /** OpenAPI 05 reopenConsultation。仅 24 小时窗口内。 */
    @PostMapping("/{id}/reopen")
    public ApiEnvelope<ConsultationProjection> reopen(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody ReasonRequest request) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.reopen(user, id, request, idempotencyKey));
    }

    /** OpenAPI 05 closeConsultation。员工主动结束,无需填写原因。 */
    @PostMapping("/{id}/close")
    public ApiEnvelope<ConsultationProjection> close(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey) {
        CurrentUser user = authzService.currentUser();
        return ok(consultationService.close(user, id, idempotencyKey));
    }

    private static <T> ApiEnvelope<T> ok(T data) {
        return ApiEnvelope.ok(data, RequestContext.get());
    }
}
