package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.ticket.entity.NotificationLog;
import com.itticket.ticket.mapper.NotificationLogMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * 通知服务(P0:模拟企微推送) —— 移植旧版 notification.js:
 * 幂等规则为「同一工单 + 同一事件 1 分钟内不重复」(以 notification_log 记录为准)。
 * 必须 @Async 且在事务提交后调用,避免回滚后发假通知。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NotificationService {

    private final NotificationLogMapper notificationLogMapper;

    @Async("notifyExecutor")
    public void sendNotification(String ticketId, String eventType, String receiverId, String channel) {
        try {
            String dedupKey = ticketId + ":" + eventType;

            Long recent = notificationLogMapper.selectCount(new QueryWrapper<NotificationLog>()
                    .eq("ticket_id", ticketId)
                    .eq("event_type", eventType)
                    .gt("created_at", LocalDateTime.now().minusMinutes(1)));
            if (recent != null && recent > 0) {
                log.info("[通知] 幂等跳过: {}", dedupKey);
                return;
            }

            // P0 模拟发送,固定 SUCCESS、非兜底
            NotificationLog record = new NotificationLog();
            record.setTicketId(ticketId);
            record.setEventType(eventType);
            record.setReceiverId(receiverId);
            record.setChannel(channel == null ? "企微" : channel);
            record.setIsFallback(0);
            record.setDeliveryStatus("SUCCESS");
            record.setCreatedAt(LocalDateTime.now());
            notificationLogMapper.insert(record);

            log.info("[通知] 已发送: {} -> {} ({})", dedupKey, receiverId, record.getChannel());
        } catch (Exception e) {
            // 通知失败不影响主流程(对应旧版 .catch(console.error))
            log.error("[通知] 发送失败: {} {} -> {}", ticketId, eventType, receiverId, e);
        }
    }

    public void sendNotification(String ticketId, String eventType, String receiverId) {
        sendNotification(ticketId, eventType, receiverId, "企微");
    }
}
