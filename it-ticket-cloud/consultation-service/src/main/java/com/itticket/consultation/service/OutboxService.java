package com.itticket.consultation.service;

import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.entity.OutboxEvent;
import com.itticket.consultation.enums.OutboxStatus;
import com.itticket.consultation.mapper.OutboxEventMapper;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 领域事件 Outbox 写入(EV-001 / EV-002)。
 *
 * <p>必须在业务事务内调用:状态迁移、主对象投影、SLA 投影和 Outbox 行同一事务提交,
 * 提交前不得写 Redis 或调用外部服务。发布由 {@code OutboxPublishScheduler} 在事务之外完成。
 *
 * <p>同一聚合的 {@code aggregate_version} 单调递增且唯一,因此一次状态迁移最多产生一个领域事实事件;
 * 需要多个副作用时由消费者按事件类型分发,而不是在这里写多条。
 */
@Service
@RequiredArgsConstructor
public class OutboxService {

    /** EV-007:事件版本只递增不复用。当前咨询域事件均为 v1。 */
    private static final int EVENT_VERSION = 1;

    public static final String AGGREGATE_CONSULTATION = "CONSULTATION";
    /** SLA 提醒与违约事件挂在 SLA 聚合上,aggregate_id 为 sla_id(EV-008 顺序键为 aggregate_id)。 */
    public static final String AGGREGATE_SLA = "SLA";

    private final OutboxEventMapper outboxEventMapper;

    /**
     * 判断某聚合是否已产生过某类事件。
     *
     * <p>用于"每个对象只提醒一次"这类去重:SQL-010 的 sla_instance 没有承载
     * "已提醒"标记的列,本服务不得擅自加列(SQL-009),因此以事件是否已存在作为幂等依据。
     */
    public boolean exists(String aggregateType, String aggregateId, String eventType) {
        Long count = outboxEventMapper.selectCount(
                com.baomidou.mybatisplus.core.toolkit.Wrappers.<OutboxEvent>lambdaQuery()
                        .eq(OutboxEvent::getAggregateType, aggregateType)
                        .eq(OutboxEvent::getAggregateId, aggregateId)
                        .eq(OutboxEvent::getEventType, eventType));
        return count != null && count > 0;
    }

    /** 咨询聚合事件的便捷入口。 */
    public void appendConsultation(String eventType, String sessionId, long aggregateVersion,
                                   Map<String, Object> payload, String actorType, String actorId) {
        append(AGGREGATE_CONSULTATION, eventType, sessionId, aggregateVersion, payload, actorType, actorId);
    }

    /**
     * @param aggregateType    聚合类型,CONSULTATION 或 SLA
     * @param eventType        SM-EVENT-001 的领域事实事件类型
     * @param aggregateId      顺序键(咨询为 session_id,SLA 为 sla_id)
     * @param aggregateVersion 聚合版本,取迁移后的实体 version;唯一键保证同版本只产生一个事件
     * @param payload          EV-008 规定的最小 payload,字段名用 snake_case
     * @param actorType        USER 或 SYSTEM
     */
    public void append(String aggregateType, String eventType, String aggregateId, long aggregateVersion,
                       Map<String, Object> payload, String actorType, String actorId) {
        LocalDateTime now = Times.nowUtc();
        String eventId = Ids.eventId();

        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("event_id", eventId);
        envelope.put("event_type", eventType);
        envelope.put("event_version", EVENT_VERSION);
        envelope.put("aggregate_type", aggregateType);
        envelope.put("aggregate_id", aggregateId);
        envelope.put("occurred_at", Times.iso(now));
        envelope.put("actor_type", actorType);
        envelope.put("actor_id", actorId);
        envelope.put("request_id", RequestContext.get());
        envelope.put("trace_id", RequestContext.get());
        envelope.put("aggregate_version", aggregateVersion);
        envelope.put("payload", payload);

        OutboxEvent event = new OutboxEvent();
        event.setEventId(eventId);
        event.setEventType(eventType);
        event.setAggregateType(aggregateType);
        event.setAggregateId(aggregateId);
        event.setEventVersion(EVENT_VERSION);
        event.setAggregateVersion(aggregateVersion);
        event.setPayloadJson(Json.write(envelope));
        event.setStatus(OutboxStatus.PENDING);
        event.setAttempts(0);
        event.setNextAttemptAt(now);
        event.setCreatedAt(now);
        event.setUpdatedAt(now);
        outboxEventMapper.insert(event);
    }
}
