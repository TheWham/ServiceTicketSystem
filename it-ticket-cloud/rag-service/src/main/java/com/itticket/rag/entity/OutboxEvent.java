package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 领域事实事件外发实体 (OutboxEvent) - 对应数据库表 `outbox_event`
 * ============================================================================
 *
 * 【契约规范说明 (EV-001 / EV-008 / SM-EVENT-001)】：
 * 1. event_type 统一使用 SCREAMING_SNAKE_CASE 领域事实事件类型，知识域为
 *    KNOWLEDGE_SUBMITTED / KNOWLEDGE_PUBLISHED / KNOWLEDGE_OFFLINE / KNOWLEDGE_INDEX_REFRESH_REQUESTED。
 * 2. 载荷只携带对象 ID、事件类型、版本、操作者与发生时间；禁止空对象。
 * 3. 状态迁移先落库、再写事件；投递失败进入补偿队列（RD-006 / RD-008），不得反向决定迁移是否合法。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@TableName("outbox_event")
public class OutboxEvent {

    /** 事件 ID，全局唯一 */
    @TableId(value = "event_id", type = IdType.INPUT)
    private String eventId;

    /** 领域事实事件类型 (SCREAMING_SNAKE_CASE) */
    private String eventType;

    /** 事件信封版本 */
    private Integer eventVersion;

    /** 聚合类型，如 KNOWLEDGE */
    private String aggregateType;

    /** 聚合 ID，如 article_id */
    private String aggregateId;

    /** 事件最小载荷 JSON */
    private String payloadJson;

    /** 投递状态：PENDING / PUBLISHED / FAILED */
    private String status;

    /** 投递尝试次数 */
    private Integer attempts;

    /** 下次重试时间 */
    private LocalDateTime nextAttemptAt;

    /** 投递成功时间 */
    private LocalDateTime publishedAt;

    /** 创建时间 */
    private LocalDateTime createdAt;
}
