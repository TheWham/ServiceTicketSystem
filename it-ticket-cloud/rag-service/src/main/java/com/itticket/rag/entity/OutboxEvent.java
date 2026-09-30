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
 * 【契约规范说明】（路径相对仓库根目录 docs/）：
 * 1. event_type 统一使用 SCREAMING_SNAKE_CASE 领域事实事件类型，知识域为
 *    KNOWLEDGE_SUBMITTED / KNOWLEDGE_PUBLISHED / KNOWLEDGE_OFFLINE / KNOWLEDGE_INDEX_REFRESH_REQUESTED
 *    （SM-EVENT-001 · specs/03-business-state-machine.md:103）。
 * 2. 信封 13 列（event_id/event_type/aggregate_type/aggregate_id/event_version/aggregate_version/
 *    payload_json/status/attempts/next_attempt_at/published_at/created_at/updated_at），
 *    载荷只携带对象 ID、事件类型、版本、操作者与发生时间；禁止空对象
 *    （EV-001 · specs/07-domain-events-outbox-redis.md:12）。
 * 3. 同一聚合按 aggregate_version 单调递增（uk_aggregate_version 唯一约束，一聚合版本一事件）；
 *    状态迁移先落库、再写事件（EV-008 · specs/07-domain-events-outbox-redis.md:85）。
 * 4. DDL 权威来源：specs/06-mysql-ddl-and-migrations.md（SQL-010 空库全量 DDL · :202）。
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

    /** 聚合类型，如 KNOWLEDGE */
    private String aggregateType;

    /** 聚合 ID，如 article_id */
    private String aggregateId;

    /** 事件信封版本（EV-001，固定 1） */
    private Integer eventVersion;

    /** 聚合版本：同一聚合上事件单调递增（取文章乐观锁 version） */
    private Long aggregateVersion;

    /** 事件最小载荷 JSON */
    private String payloadJson;

    /** 投递状态：PENDING / PUBLISHED / FAILED / DEAD_LETTER */
    private String status;

    /** 投递尝试次数 */
    private Integer attempts;

    /** 下次重试时间 */
    private LocalDateTime nextAttemptAt;

    /** 投递成功时间 */
    private LocalDateTime publishedAt;

    /** 创建时间 */
    private LocalDateTime createdAt;

    /** 更新时间 */
    private LocalDateTime updatedAt;
}
