package com.itticket.consultation.scheduler;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.entity.Assignment;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.ExceptionQueueItem;
import com.itticket.consultation.entity.SlaInstance;
import com.itticket.consultation.enums.AssignmentEndReason;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.mapper.ConsultationMapper;
import com.itticket.consultation.service.AssignmentService;
import com.itticket.consultation.service.AuditService;
import com.itticket.consultation.service.ConsultationSlaService;
import com.itticket.consultation.service.OutboxService;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * 人工咨询响应超时自动转派(PRD 8.4、AC-08/AC-09;防御规则 RD-004、RD-005)。
 *
 * <p>每轮扫描已过响应截止时间且仍在进行中的分配任务,对每条:
 * <ol>
 *   <li>用 {@code end_reason IS NULL} 作为条件更新抢占任务 —— 这就是 RD-004 要求的
 *       "带版本条件的更新",保证同一超时事件只被处理一次,多实例并发扫描也不会重复转派;</li>
 *   <li>首次超时写入 SLA 违约事实并发 SLA_BREACHED;违约一经产生不可被后续操作删除(PRD 11.2);</li>
 *   <li>按序转派下一名候选人;候选人耗尽则进入平台管理员异常队列,不无限循环(RD-005)。</li>
 * </ol>
 *
 * <p>转派不重置咨询级响应 SLA 投影(RD-005),新候选人的计时由新分配任务的 responseDeadline 承载。
 *
 * <p>事务边界用 {@link TransactionTemplate} 而不是 {@code @Transactional}:
 * 同类内部调用不会经过 Spring 代理,注解在这里是无效的。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ConsultationResponseTimeoutScheduler {

    /** 单轮处理上限,避免一次扫描长时间占用连接(RD-007 并发隔离)。 */
    private static final int BATCH_SIZE = 50;

    private final AssignmentService assignmentService;
    private final ConsultationSlaService slaService;
    private final ConsultationMapper consultationMapper;
    private final OutboxService outboxService;
    private final AuditService auditService;
    private final TransactionTemplate transactionTemplate;

    @Scheduled(fixedDelayString = "${itticket.consultation.scheduler.response-timeout-delay-ms:30000}")
    public void scan() {
        RequestContext.set("sys_" + UUID.randomUUID().toString().replace("-", ""));
        try {
            LocalDateTime now = Times.nowUtc();
            List<Assignment> overdue = assignmentService.findOverdueAssignments(now, BATCH_SIZE);
            for (Assignment assignment : overdue) {
                try {
                    transactionTemplate.executeWithoutResult(status -> handleOverdue(assignment, now));
                } catch (RuntimeException e) {
                    // 单条失败不影响同批其他任务;错误分类进日志供 RD-010 告警
                    log.error("[timeout] 处理超时分配失败 assignmentId={} sessionId={}",
                            assignment.getAssignmentId(), assignment.getBizId(), e);
                }
            }
        } finally {
            RequestContext.clear();
        }
    }

    private void handleOverdue(Assignment assignment, LocalDateTime now) {
        // 抢占:只有把 end_reason 从 NULL 改成 TIMEOUT 成功的那个实例继续往下走
        if (!assignmentService.endAssignment(assignment.getAssignmentId(),
                AssignmentEndReason.TIMEOUT, null)) {
            return;
        }
        String sessionId = assignment.getBizId();
        Consultation consultation = consultationMapper.selectById(sessionId);
        if (consultation == null || consultation.getStatus() != ConsultationStatus.WAITING_ENGINEER) {
            // 期间已有工程师响应或会话已终止,无需转派
            return;
        }

        recordBreach(sessionId, now);
        auditService.record("SYSTEM", "CONSULTATION_RESPONSE_TIMEOUT",
                AuditService.OBJECT_CONSULTATION, sessionId,
                Map.of("engineer_id", assignment.getEngineerId()), null,
                "响应超时,自动转派下一候选人");

        Optional<Assignment> next = assignmentService.assignNextCandidate(
                sessionId, consultation.getCategoryId(), now);
        if (next.isEmpty()) {
            assignmentService.enqueueException(sessionId,
                    ExceptionQueueItem.REASON_CANDIDATES_EXHAUSTED,
                    "响应超时后候选工程师已耗尽,需平台管理员介入");
            // 责任人置空,避免已超时的工程师继续被当作当前责任人(AX-001 当前责任关系)
            updateEngineer(consultation, null, now);
            log.warn("[timeout] 咨询 {} 候选工程师耗尽,已进入异常队列", sessionId);
            return;
        }

        long newVersion = updateEngineer(consultation, next.get().getEngineerId(), now);
        // 转派成功也是一次"转人工"事实,通知与分配消费者据此接力(EV-008)
        outboxService.appendConsultation("CONSULTATION_TRANSFERRED", sessionId, newVersion,
                Map.of("session_id", sessionId,
                        "category_id", consultation.getCategoryId(),
                        "assignment_id", next.get().getAssignmentId()),
                "SYSTEM", "SYSTEM");
    }

    /** 首次超时才写违约;重复扫描因 status 条件不满足而不会重复发事件(RD-012)。 */
    private void recordBreach(String sessionId, LocalDateTime now) {
        SlaInstance sla = slaService.find(sessionId);
        if (sla == null || !slaService.markBreached(sla, now)) {
            return;
        }
        outboxService.append(OutboxService.AGGREGATE_SLA, "SLA_BREACHED", sla.getSlaId(),
                sla.getVersion() + 1,
                Map.of("sla_id", sla.getSlaId(),
                        "aggregate_id", sessionId,
                        "breached_at", Times.iso(now)),
                "SYSTEM", "SYSTEM");
    }

    /** 乐观锁更新责任人,返回新版本号;冲突时抛出由上层记录,不盲目重试(RD-001)。 */
    private long updateEngineer(Consultation consultation, String engineerId, LocalDateTime now) {
        long newVersion = consultation.getVersion() + 1;
        int rows = consultationMapper.update(null, Wrappers.<Consultation>lambdaUpdate()
                .eq(Consultation::getSessionId, consultation.getSessionId())
                .eq(Consultation::getVersion, consultation.getVersion())
                .set(Consultation::getCurrentEngineerId, engineerId)
                .set(Consultation::getVersion, newVersion)
                .set(Consultation::getUpdatedAt, now));
        if (rows == 0) {
            throw new IllegalStateException("咨询 " + consultation.getSessionId() + " 在转派期间被并发修改");
        }
        return newVersion;
    }
}
