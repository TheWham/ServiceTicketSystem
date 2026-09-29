package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.ticket.entity.Notification;
import com.itticket.ticket.mapper.NotificationMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 通知服务 —— PRD-Ultimate §14。
 * 幂等：dedup_key = event_id:receiver:channel，生命周期唯一（§14.3，防重放，非时间窗）。
 * 渠道：站内（INBOX）＋高优先级邮件（EMAIL，一期 Mock）。
 * 重试：站内同步重试 3 次；邮件按指数退避。最终失败 → 管理员异常队列。
 * 必须 @Async 且在事务提交后调用，避免回滚后发假通知。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NotificationService {

    private final NotificationMapper notificationMapper;
    private final ExceptionQueueService exceptionQueueService;
    private final com.itticket.ticket.mapper.TicketMapper ticketMapper;

    private static final int MAX_RETRY = 3;

    /** 事件码 → 中文动作文案（§14.2 行动导向，面向用户可读） */
    private static final java.util.Map<String, String> EVENT_LABEL = java.util.Map.ofEntries(
            java.util.Map.entry("SUBMIT_SUCCESS", "工单已提交"),
            java.util.Map.entry("ASSIGNED", "新工单待接单"),
            java.util.Map.entry("ACCEPTED", "工程师已接单"),
            java.util.Map.entry("REQUEST_SUPPLEMENT", "请补充工单信息"),
            java.util.Map.entry("SUPPLEMENTED", "已补充信息"),
            java.util.Map.entry("EXTERNAL_WAIT", "工单转入外部等待"),
            java.util.Map.entry("EXTERNAL_RESUMED", "外部等待已恢复"),
            java.util.Map.entry("SUBMIT_RESOLUTION", "解决方案待验收"),
            java.util.Map.entry("ACCEPT_APPROVED", "验收已通过"),
            java.util.Map.entry("ACCEPT_REJECTED", "验收被驳回"),
            java.util.Map.entry("AUTO_ACCEPTED", "工单已自动验收"),
            java.util.Map.entry("CANCELLED", "工单已撤销"),
            java.util.Map.entry("CLOSED", "工单已关闭"),
            java.util.Map.entry("REOPENED", "工单已重新打开"),
            java.util.Map.entry("SUPPLEMENT_TIMEOUT_CLOSED", "逾期未补充,工单已关闭"),
            java.util.Map.entry("SLA_NEAR", "SLA 即将超时"),
            java.util.Map.entry("SLA_BREACHED", "SLA 已违约"),
            java.util.Map.entry("ROUTE_FAILED", "工单路由失败，待管理员分配")
    );

    /**
     * 发送通知（站内）。在事务提交后异步调用。
     *
     * @param eventId    领域事件实例 ID（§21.4，如 TICKET_ASSIGNED:{ticketId}:{seq}）
     * @param receiverId 接收人
     * @param title      标题
     * @param content    正文
     * @param actionUrl  待办行动入口（查看≠行动 §14.2）
     */
    @Async("notifyExecutor")
    public void sendInbox(String eventId, String receiverId, String title, String content, String actionUrl) {
        deliver(eventId, receiverId, "IN_APP", title, content, actionUrl);
    }

    /** 高优先级邮件（一期 Mock，仅记录日志）。 */
    @Async("notifyExecutor")
    public void sendEmail(String eventId, String receiverId, String title, String content) {
        deliver(eventId, receiverId, "EMAIL", title, content, null);
    }

    /** 便捷：仅站内。自动生成中文文案 + 待办跳转（§14.2 查看≠行动，必须可点进待办）。 */
    @Async("notifyExecutor")
    public void sendNotification(String ticketId, String eventType, String receiverId) {
        String eventId = eventType + ":" + ticketId;
        // 查工单标题（失败降级为单号，不阻塞通知）
        String ticketTitle = ticketId;
        try {
            com.itticket.ticket.entity.Ticket t = ticketMapper.selectById(ticketId);
            if (t != null && t.getTitle() != null && !t.getTitle().isBlank()) {
                ticketTitle = t.getTitle();
            }
        } catch (Exception e) {
            log.warn("[通知] 查询工单标题失败,降级为单号: {}", ticketId);
        }
        String label = EVENT_LABEL.getOrDefault(eventType, eventType);
        String title = "【" + label + "】" + ticketTitle;
        String content = "工单 " + ticketId + " " + label + "，点击查看详情处理。";
        String actionUrl = "/tickets/" + ticketId;
        deliver(eventId, receiverId, "IN_APP", title, content, actionUrl);
    }

    /**
     * 投递主流程：幂等 → 尝试发送 → 重试 → 失败入异常队列。
     */
    private void deliver(String eventId, String receiverId, String channel,
                         String title, String content, String actionUrl) {
        String dedupKey = eventId + ":" + receiverId + ":" + channel;

        // 幂等占位：dedup_key 唯一键，冲突即跳过（生命周期唯一 §14.3）
        Notification n = new Notification();
        n.setNotificationId("NTF" + UUID.randomUUID().toString().replace("-", "").substring(0, 29));
        n.setEventId(eventId);
        n.setReceiverId(receiverId);
        n.setChannel(channel);
        n.setDedupKey(dedupKey);
        n.setTitle(title);
        n.setContent(content);
        n.setActionUrl(actionUrl);
        n.setStatus("PENDING");
        n.setAttempts(0);
        n.setCreatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        n.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        try {
            notificationMapper.insert(n);
        } catch (DuplicateKeyException e) {
            log.info("[通知] 幂等跳过: {}", dedupKey);
            return;
        }

        // 尝试发送 + 重试
        boolean sent = false;
        String lastError = null;
        for (int attempt = 1; attempt <= MAX_RETRY && !sent; attempt++) {
            try {
                doSend(n);
                sent = true;
            } catch (Exception e) {
                lastError = e.getMessage();
                log.warn("[通知] 第 次发送失败: {} -> {} ({}): {}", attempt, eventId, receiverId, channel, lastError);
            }
        }

        // 更新最终状态
        Notification upd = new Notification();
        upd.setNotificationId(n.getNotificationId());
        upd.setStatus(sent ? "SENT" : "FAILED");
        upd.setAttempts(sent ? 1 : MAX_RETRY);
        upd.setLastError(sent ? null : lastError);
        upd.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        notificationMapper.updateById(upd);

        if (!sent) {
            // 最终失败 → 管理员异常记录（§14.3）
            exceptionQueueService.raise("NOTIFICATION", n.getNotificationId(),
                    ExceptionQueueService.TYPE_NOTIFY_FAILED,
                    "通知发送失败", dedupKey + " 已重试 " + MAX_RETRY + " 次: " + lastError, null);
            log.error("[通知] 最终失败已入异常队列: {}", dedupKey);
        } else {
            log.info("[通知] 已发送: {} -> {} ({})", dedupKey, receiverId, channel);
        }
    }

    /** 实际发送（一期：站内落库即送达；邮件 Mock 仅记录日志，不打异常） */
    private void doSend(Notification n) {
        if ("EMAIL".equals(n.getChannel())) {
            // 邮件 Mock：一期不真实发送，仅日志
            log.info("[通知·邮件Mock] -> {} | | {}", n.getReceiverId(), n.getTitle(), n.getContent());
            return;
        }
        // 站内：落库即视为送达（notification 表本身就是在通知中心的载体）
        log.info("[通知·站内] -> {} | {}", n.getReceiverId(), n.getTitle());
    }
}
