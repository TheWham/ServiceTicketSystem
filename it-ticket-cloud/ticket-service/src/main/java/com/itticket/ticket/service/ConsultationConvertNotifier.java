package com.itticket.ticket.service;

import com.itticket.common.web.UserContext;
import com.itticket.ticket.feign.ConsultationClient;
import com.itticket.ticket.feign.ConvertedNotice;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

/**
 * 咨询转工单回调(PRD 9.1 / SM-CONSULT-001:先有工单、后有终态)。
 *
 * <p>工单以 source_session_id 建单成功、事务提交后,通知 consultation-service
 * 把咨询迁移到 CONVERTED_TO_TICKET。与 NotificationService 同模式:
 * 必须 @Async 且在事务提交后调用,咨询服务不可用时不占用业务线程、不阻塞建单响应
 * (RD-013:外部依赖失败不得阻止员工提交工单)。失败只记日志——工单已创建是既成事实,
 * 咨询侧保持非终态,可由员工重新触发或人工补偿。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ConsultationConvertNotifier {

    private final ConsultationClient consultationClient;

    @Async("notifyExecutor")
    public void notifyConverted(String sessionId, String ticketId, UserContext.CurrentUser creator) {
        try {
            consultationClient.markConverted(
                    sessionId,
                    "ticket-converted:" + ticketId,
                    "req-" + ticketId,
                    creator.getUserId(),
                    urlEncodeHeader(creator.getName()),
                    creator.getRole(),
                    urlEncodeHeader(creator.getDepartment()),
                    new ConvertedNotice(ticketId));
            log.info("[TICKET] 咨询 {} 已转工单 {}", sessionId, ticketId);
        } catch (Exception e) {
            log.warn("[TICKET] 咨询 {} 转单回调失败(工单 {} 已创建,咨询侧待补偿): {}",
                    sessionId, ticketId, e.getMessage());
        }
    }

    /** 网关注入的中文头经 URL 编码,这里保持同样约定(consultation 侧 UserContextInterceptor 会解码)。 */
    private String urlEncodeHeader(String value) {
        if (value == null) return null;
        return java.net.URLEncoder.encode(value, java.nio.charset.StandardCharsets.UTF_8);
    }
}
