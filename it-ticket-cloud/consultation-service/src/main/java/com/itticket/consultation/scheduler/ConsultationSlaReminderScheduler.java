package com.itticket.consultation.scheduler;

import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.entity.Assignment;
import com.itticket.consultation.entity.SlaInstance;
import com.itticket.consultation.service.AssignmentService;
import com.itticket.consultation.service.ConsultationSlaService;
import com.itticket.consultation.service.OutboxService;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 响应 SLA 临近超时提醒(PRD 11.3:响应 SLA 在第 8 个工作分钟提醒)。
 *
 * <p>提醒只发一次:sla_instance 没有"已提醒"列(SQL-010 未定义,本服务不得擅自加列),
 * 因此以 Outbox 中是否已存在该 SLA 的 SLA_NEAR_BREACH 事件作为幂等依据(EV-002 的
 * event 唯一性天然可复用)。提醒失败不改变 SLA 结果(RD-004),因此本调度器不写 SLA 状态。
 *
 * <p>提醒时刻按服务日历从"有效分配时刻"推算(AX-002),不使用墙钟差值,
 * 也不使用客户端时间(RD-004)。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ConsultationSlaReminderScheduler {

    private static final int BATCH_SIZE = 100;
    private static final String EVENT_NEAR_BREACH = "SLA_NEAR_BREACH";
    /** PRD 11.3 默认阈值为目标时长的 80%;响应 SLA 另按第 8 个工作分钟提醒。 */
    private static final int THRESHOLD_PERCENT = 80;

    private final ConsultationSlaService slaService;
    private final AssignmentService assignmentService;
    private final OutboxService outboxService;

    @Scheduled(fixedDelayString = "${itticket.consultation.scheduler.sla-reminder-delay-ms:60000}")
    public void scan() {
        RequestContext.set("sys_" + UUID.randomUUID().toString().replace("-", ""));
        try {
            LocalDateTime now = Times.nowUtc();
            List<SlaInstance> running = slaService.findRunning(BATCH_SIZE);
            for (SlaInstance sla : running) {
                try {
                    remindIfDue(sla, now);
                } catch (RuntimeException e) {
                    log.error("[sla-remind] 处理失败 slaId={} sessionId={}",
                            sla.getSlaId(), sla.getBizId(), e);
                }
            }
        } finally {
            RequestContext.clear();
        }
    }

    private void remindIfDue(SlaInstance sla, LocalDateTime now) {
        if (outboxService.exists(OutboxService.AGGREGATE_SLA, sla.getSlaId(), EVENT_NEAR_BREACH)) {
            return;
        }
        Optional<Assignment> active = assignmentService.activeAssignment(sla.getBizId());
        LocalDateTime startedAt = active.map(Assignment::getAssignedAt).orElse(sla.getCreatedAt());
        LocalDateTime remindAt = slaService.nearBreachAt(startedAt);
        if (now.isBefore(remindAt)) {
            return;
        }
        long version = slaService.bumpVersionForReminder(sla);
        if (version < 0) {
            // 并发扫描已抢先处理,或 SLA 已不在计时状态
            return;
        }
        outboxService.append(OutboxService.AGGREGATE_SLA, EVENT_NEAR_BREACH, sla.getSlaId(), version,
                Map.of("sla_id", sla.getSlaId(),
                        "aggregate_id", sla.getBizId(),
                        "threshold_percent", THRESHOLD_PERCENT),
                "SYSTEM", "SYSTEM");
        log.info("[sla-remind] 响应 SLA 临近超时 slaId={} sessionId={}", sla.getSlaId(), sla.getBizId());
    }
}
