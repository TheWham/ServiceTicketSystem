package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 通知记录(it_ticket.notification_log),兼做 1 分钟幂等去重依据 */
@Data
@TableName("notification_log")
public class NotificationLog {
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private String ticketId;
    private String eventType;
    private String receiverId;
    /** 企微/短信/站内 */
    private String channel;
    private Integer isFallback;
    /** PENDING/SUCCESS/FAILED */
    private String deliveryStatus;
    private LocalDateTime createdAt;
}
