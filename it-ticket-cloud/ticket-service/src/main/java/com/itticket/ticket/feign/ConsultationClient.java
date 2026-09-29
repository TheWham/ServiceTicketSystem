package com.itticket.ticket.feign;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;

import java.util.Map;

/**
 * 调用 consultation-service 的内部接口(经 Nacos 直连,不经网关;与 UserClient 同模式)。
 *
 * <p>咨询转工单回调:工单以 source_session_id 建单成功后,由本接口通知咨询侧
 * 迁移到 CONVERTED_TO_TICKET(先有工单、后有终态)。调用方必须透传发起员工的
 * X-User-* 身份头与 Idempotency-Key,咨询侧据此做归属校验(markConverted requireCreator)。
 */
@FeignClient(name = "consultation-service", contextId = "consultationClient")
public interface ConsultationClient {

    @PostMapping("/api/internal/consultations/{id}/converted")
    Map<String, Object> markConverted(
            @PathVariable("id") String sessionId,
            @RequestHeader("Idempotency-Key") String idempotencyKey,
            @RequestHeader("X-Request-Id") String requestId,
            @RequestHeader("X-User-Id") String userId,
            @RequestHeader("X-User-Name") String userName,
            @RequestHeader("X-User-Role") String userRole,
            @RequestHeader(value = "X-User-Dept", required = false) String userDept,
            @RequestBody ConvertedNotice notice);
}
