package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;

/** 通知（PRD §14：幂等键生命周期唯一；最终失败入管理员异常记录） */
@Data
@TableName("notification")
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class Notification {
    @TableId(value = "notification_id", type = IdType.INPUT)
    private String notificationId;
    /** 领域事件实例 ID（§21.4） */
    private String eventId;
    private String receiverId;
    /** IN_APP / EMAIL */
    private String channel;
    /** event_id:receiver:channel（生命周期唯一 §14.3） */
    private String dedupKey;
    private String title;
    private String content;
    /** 待办行动入口（查看≠行动 §14.2） */
    private String actionUrl;
    /** PENDING / SENT / FAILED */
    private String status;
    /** 站内重试 3 次；邮件指数退避 */
    private Integer attempts;
    private String lastError;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
