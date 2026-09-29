package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.ConsultationProjection;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.ConsultationService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 服务间内部接口:咨询转工单的回写。
 *
 * <p>工单事实由 ticket-service 拥有(AI-001 明确 AI 不得创建工单,咨询服务也不写工单表)。
 * ticket-service 以 source_session_id 建单成功后调用本接口,咨询侧才迁移到 CONVERTED_TO_TICKET,
 * 保证"先有工单、后有终态",不会出现指向不存在工单的 converted_ticket_id。
 *
 * <p>调用方必须透传发起员工的身份头:归属校验仍然按员工本人执行(AX-001 不信任请求体中的操作者)。
 */
@Validated
@RestController
@RequestMapping("/api/internal/consultations")
@RequiredArgsConstructor
public class InternalConsultationController {

    private final ConsultationService consultationService;
    private final AuthzService authzService;

    public record ConvertedNotice(@NotBlank @Size(max = 32) String ticketId) {
    }

    @PostMapping("/{id}/converted")
    public ApiEnvelope<ConsultationProjection> markConverted(
            @PathVariable String id,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @Valid @RequestBody ConvertedNotice notice) {
        return ApiEnvelope.ok(
                consultationService.markConverted(authzService.currentUser(), id,
                        notice.ticketId(), idempotencyKey),
                RequestContext.get());
    }
}
