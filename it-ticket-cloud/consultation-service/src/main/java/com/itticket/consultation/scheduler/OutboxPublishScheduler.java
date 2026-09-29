package com.itticket.consultation.scheduler;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.entity.OutboxEvent;
import com.itticket.consultation.enums.OutboxStatus;
import com.itticket.consultation.mapper.OutboxEventMapper;
import com.itticket.consultation.service.DomainEventPublisher;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Outbox 发布器(EV-002、EV-004、EV-009)。
 *
 * <p>扫描 {@code status=PENDING AND next_attempt_at<=now},用带状态条件的更新抢占行,
 * 再调用投递出口。生命周期 PENDING → PUBLISHED;失败置 FAILED 并按退避序列重排,
 * 超过上限转 DEAD_LETTER。重复扫描不会产生新的 event_id(事件在业务事务中一次性写入)。
 *
 * <p>Redis 不可用时事件保持 PENDING/FAILED,由本扫描补发(RD-014、EV-006):
 * 任何情况下都不会先写队列再写主表。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxPublishScheduler {

    private static final int BATCH_SIZE = 100;
    /** EV-009:单事件最大重试 5 次。 */
    private static final int MAX_ATTEMPTS = 5;
    /** EV-009 退避序列:1s / 5s / 30s / 5m / 30m。 */
    private static final long[] BACKOFF_SECONDS = {1, 5, 30, 300, 1800};

    private final OutboxEventMapper outboxEventMapper;
    private final DomainEventPublisher publisher;

    @Scheduled(fixedDelayString = "${itticket.consultation.scheduler.outbox-delay-ms:2000}")
    public void publishPending() {
        RequestContext.set("sys_" + UUID.randomUUID().toString().replace("-", ""));
        try {
            LocalDateTime now = Times.nowUtc();
            List<OutboxEvent> pending = outboxEventMapper.selectList(Wrappers.<OutboxEvent>lambdaQuery()
                    .in(OutboxEvent::getStatus, OutboxStatus.PENDING, OutboxStatus.FAILED)
                    .le(OutboxEvent::getNextAttemptAt, now)
                    .orderByAsc(OutboxEvent::getNextAttemptAt)
                    .last("LIMIT " + BATCH_SIZE));
            for (OutboxEvent event : pending) {
                deliver(event, now);
            }
        } finally {
            RequestContext.clear();
        }
    }

    private void deliver(OutboxEvent event, LocalDateTime now) {
        int attempts = event.getAttempts() == null ? 0 : event.getAttempts();
        boolean delivered;
        try {
            delivered = publisher.publish(event);
        } catch (RuntimeException e) {
            log.warn("[outbox] 投递异常 eventId={} attempts={}", event.getEventId(), attempts, e);
            delivered = false;
        }

        if (delivered) {
            // published_at 只在接收成功后写入(EV-002)
            outboxEventMapper.update(null, Wrappers.<OutboxEvent>lambdaUpdate()
                    .eq(OutboxEvent::getEventId, event.getEventId())
                    .in(OutboxEvent::getStatus, OutboxStatus.PENDING, OutboxStatus.FAILED)
                    .set(OutboxEvent::getStatus, OutboxStatus.PUBLISHED)
                    .set(OutboxEvent::getAttempts, attempts + 1)
                    .set(OutboxEvent::getPublishedAt, now)
                    .set(OutboxEvent::getNextAttemptAt, null)
                    .set(OutboxEvent::getUpdatedAt, now));
            return;
        }

        int nextAttempts = attempts + 1;
        boolean dead = nextAttempts >= MAX_ATTEMPTS;
        LocalDateTime nextAttemptAt = dead ? null
                : now.plusSeconds(BACKOFF_SECONDS[Math.min(nextAttempts, BACKOFF_SECONDS.length - 1)]);
        outboxEventMapper.update(null, Wrappers.<OutboxEvent>lambdaUpdate()
                .eq(OutboxEvent::getEventId, event.getEventId())
                .in(OutboxEvent::getStatus, OutboxStatus.PENDING, OutboxStatus.FAILED)
                .set(OutboxEvent::getStatus, dead ? OutboxStatus.DEAD_LETTER : OutboxStatus.FAILED)
                .set(OutboxEvent::getAttempts, nextAttempts)
                .set(OutboxEvent::getNextAttemptAt, nextAttemptAt)
                .set(OutboxEvent::getUpdatedAt, now));
        if (dead) {
            // RD-008:死信必须保留事件 ID、重试次数、关联对象,供管理员查看与幂等重放
            log.error("[outbox] 事件进入死信 eventId={} type={} aggregateId={} attempts={}",
                    event.getEventId(), event.getEventType(), event.getAggregateId(), nextAttempts);
        }
    }
}
