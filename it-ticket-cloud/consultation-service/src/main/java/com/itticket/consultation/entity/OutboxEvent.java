package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.OutboxStatus;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 领域事件 Outbox(DM-004 / EV-002)。
 * 与状态迁移在同一事务内提交;提交前不得写队列或调用外部服务。
 * (aggregateType, aggregateId, aggregateVersion) 唯一,保证同一聚合版本只产生一个事件。
 */
@Data
@TableName("outbox_event")
public class OutboxEvent {

    @TableId(value = "event_id", type = IdType.INPUT)
    private String eventId;
    private String eventType;
    private String aggregateType;
    private String aggregateId;
    private Integer eventVersion;
    private Long aggregateVersion;
    private String payloadJson;
    private OutboxStatus status;
    private Integer attempts;
    private LocalDateTime nextAttemptAt;
    private LocalDateTime publishedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
