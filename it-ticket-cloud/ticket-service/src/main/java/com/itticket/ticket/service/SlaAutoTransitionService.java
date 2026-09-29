package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * SLA 自动化流转调度（F-08 延伸，状态机超时自动流转）。
 * - 48h 自动验收：PENDING_ACCEPTANCE 超 48 工作小时未操作 → COMPLETED（auto_accept）
 * - 72h 逾期补充自动关闭：PENDING_SUPPLEMENT 超 72 工作小时未补充 → CLOSED（supplement_timeout）
 * 截止时间按 WorkCalendar 工作时长推算，进入对应状态时记录 updatedAt 起算。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SlaAutoTransitionService {

    private static final long AUTO_ACCEPT_SECONDS = 48L * 3600;      // 48 工作小时
    private static final long SUPPLEMENT_TIMEOUT_SECONDS = 72L * 3600; // 72 工作小时
    private static final long EXTERNAL_WAIT_SECONDS = 40L * 3600;      // 5 个工作日(8h×5)，§9.5 超 5 工作日进异常队列

    private final TicketMapper ticketMapper;
    private final TicketFlowLogMapper flowLogMapper;
    private final WorkCalendarService workCalendarService;
    private final SlaService slaService;
    private final NotificationService notificationService;
    private final ExceptionQueueService exceptionQueueService;

    /** 每 5 分钟扫描一次自动化流转 */
    @Scheduled(fixedDelay = 300000, initialDelay = 90000)
    public void scan() {
        try {
            scanAutoAccept();
        } catch (Exception e) {
            log.error("[SLA自动流转] 自动验收扫描异常", e);
        }
        try {
            scanSupplementTimeout();
        } catch (Exception e) {
            log.error("[SLA自动流转] 逾期补充关闭扫描异常", e);
        }
        try {
            scanExternalWaitTimeout();
        } catch (Exception e) {
            log.error("[SLA自动流转] 外部等待超时扫描异常", e);
        }
    }

    /** 外部等待超时（§9.5）：PENDING_EXTERNAL 超 5 个工作日 → 进异常队列（不自动流转，人工介入） */
    void scanExternalWaitTimeout() {
        List<Ticket> pending = ticketMapper.selectList(new QueryWrapper<Ticket>()
                .eq("status", TicketStatus.PENDING_EXTERNAL.getValue()));
        for (Ticket t : pending) {
            LocalDateTime deadline = workCalendarService.addWorkSeconds(
                    t.getUpdatedAt() != null ? t.getUpdatedAt() : t.getCreatedAt(), EXTERNAL_WAIT_SECONDS);
            if (!LocalDateTime.now(java.time.ZoneOffset.UTC).isBefore(deadline)) {
                exceptionQueueService.raise("TICKET", t.getTicketId(),
                        ExceptionQueueService.TYPE_LONG_PENDING,
                        "外部等待超时", "外部依赖等待已超过 5 个工作日仍未解决，请人工介入推动",
                        t.getPriority());
            }
        }
    }

    /** 48h 自动验收：PENDING_ACCEPTANCE 且 updatedAt + 48 工作小时已到 → COMPLETED */
    void scanAutoAccept() {
        List<Ticket> pending = ticketMapper.selectList(new QueryWrapper<Ticket>()
                .eq("status", TicketStatus.PENDING_ACCEPTANCE.getValue()));
        for (Ticket t : pending) {
            LocalDateTime deadline = workCalendarService.addWorkSeconds(
                    t.getUpdatedAt() != null ? t.getUpdatedAt() : t.getCreatedAt(), AUTO_ACCEPT_SECONDS);
            if (!LocalDateTime.now(java.time.ZoneOffset.UTC).isBefore(deadline)) {
                autoAccept(t);
            }
        }
    }

    @Transactional
    public void autoAccept(Ticket t) {
        int rows = ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
                .eq(Ticket::getTicketId, t.getTicketId())
                .eq(Ticket::getStatus, TicketStatus.PENDING_ACCEPTANCE)
                .set(Ticket::getStatus, TicketStatus.COMPLETED)
                .set(Ticket::getSolvedAt, LocalDateTime.now(java.time.ZoneOffset.UTC))
                .set(Ticket::getCompletedAt, LocalDateTime.now(java.time.ZoneOffset.UTC))
                .set(Ticket::getUpdatedAt, LocalDateTime.now(java.time.ZoneOffset.UTC)));
        if (rows == 0) return;
        slaService.stop(t.getTicketId());
        insertFlow(t.getTicketId(), TicketStatus.PENDING_ACCEPTANCE, TicketStatus.COMPLETED, "TICKET_AUTO_ACCEPT", "SYSTEM", "48小时未操作自动验收");
        notificationService.sendNotification(t.getTicketId(), "AUTO_ACCEPTED", t.getCreatorId());
        log.info("[SLA自动流转] 自动验收: {}", t.getTicketId());
    }

    /** 72h 逾期补充自动关闭：PENDING_SUPPLEMENT 且 updatedAt + 72 工作小时已到 → CLOSED */
    void scanSupplementTimeout() {
        List<Ticket> pending = ticketMapper.selectList(new QueryWrapper<Ticket>()
                .eq("status", TicketStatus.PENDING_SUPPLEMENT.getValue()));
        for (Ticket t : pending) {
            LocalDateTime deadline = workCalendarService.addWorkSeconds(
                    t.getUpdatedAt() != null ? t.getUpdatedAt() : t.getCreatedAt(), SUPPLEMENT_TIMEOUT_SECONDS);
            if (!LocalDateTime.now(java.time.ZoneOffset.UTC).isBefore(deadline)) {
                supplementTimeoutClose(t);
            }
        }
    }

    @Transactional
    public void supplementTimeoutClose(Ticket t) {
        int rows = ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
                .eq(Ticket::getTicketId, t.getTicketId())
                .eq(Ticket::getStatus, TicketStatus.PENDING_SUPPLEMENT)
                .set(Ticket::getStatus, TicketStatus.CLOSED)
                .set(Ticket::getClosedAt, LocalDateTime.now(java.time.ZoneOffset.UTC))
                .set(Ticket::getUpdatedAt, LocalDateTime.now(java.time.ZoneOffset.UTC)));
        if (rows == 0) return;
        slaService.cancel(t.getTicketId());
        insertFlow(t.getTicketId(), TicketStatus.PENDING_SUPPLEMENT, TicketStatus.CLOSED, "TICKET_AUTO_CLOSE", "SYSTEM", "72小时未补充自动关闭");
        if (t.getCreatorId() != null) {
            notificationService.sendNotification(t.getTicketId(), "SUPPLEMENT_TIMEOUT_CLOSED", t.getCreatorId());
        }
        if (t.getAssigneeId() != null) {
            notificationService.sendNotification(t.getTicketId(), "SUPPLEMENT_TIMEOUT_CLOSED", t.getAssigneeId());
        }
        log.info("[SLA自动流转] 逾期补充自动关闭: {}", t.getTicketId());
    }

    private void insertFlow(String ticketId, TicketStatus from, TicketStatus to, String eventCode, String operatorId, String remark) {
        TicketFlowLog flow = new TicketFlowLog();
        flow.setTicketId(ticketId);
        flow.setFromStatus(from.getValue());
        flow.setToStatus(to.getValue());
        flow.setEvent(eventCode);
        flow.setOperatorId(operatorId);
        flow.setReason(remark);
        flow.setOccurredAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        flowLogMapper.insert(flow);
    }
}
