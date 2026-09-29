package com.itticket.consultation.service;

import com.itticket.consultation.entity.OutboxEvent;
import lombok.extern.slf4j.Slf4j;

/**
 * Outbox 投递出口(EV-003)。
 *
 * <p>契约默认目标是 Redis Streams + Consumer Group。当前技术栈尚未引入 Redis,
 * 因此提供一个记录型实现作为接线点:MySQL 仍然是事实源(EV-002、DM-006),
 * 换成 Redis 实现时只需替换本接口的实现类,Outbox 表结构、重试与死信语义不变。
 *
 * <p>实现必须满足:投递成功才返回 true;失败返回 false 或抛异常,由调度器按
 * EV-009 的退避序列重试,超过上限转 DEAD_LETTER(EV-004)。
 */
public interface DomainEventPublisher {

    boolean publish(OutboxEvent event);

    /**
     * 一期默认实现:把 envelope 写入结构化日志。
     *
     * <p>它是"可观测的显式降级"而不是假成功 —— 事件确实离开了服务边界并可被日志管道采集,
     * 但不具备消费确认能力,因此接入真实队列前不得宣称满足 EV-003 的端到端投递语义(TR-005)。
     */
    @Slf4j
    class Logging implements DomainEventPublisher {

        @Override
        public boolean publish(OutboxEvent event) {
            log.info("[outbox] eventId={} type={} aggregate={}/{} version={} payload={}",
                    event.getEventId(), event.getEventType(), event.getAggregateType(),
                    event.getAggregateId(), event.getAggregateVersion(), event.getPayloadJson());
            return true;
        }
    }
}
