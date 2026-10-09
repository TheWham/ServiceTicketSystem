package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.ticket.entity.SlaInstance;
import com.itticket.ticket.entity.SlaPause;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.mapper.SlaInstanceMapper;
import com.itticket.ticket.mapper.SlaPauseMapper;
import com.itticket.ticket.mapper.TicketMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * SLA 服务 —— PRD-Ultimate F-08 / §11。
 * 完成 SLA 自工单创建起算（§11.2）；补充/外部等待期间暂停（§11.3）；
 * 验收阶段不消耗完成 SLA（§11.4）；breach_at 一旦写入不可删除（§11.2）。
 * 目标工作秒按优先级：P0 4h / P1 8h / P2 16h / P3 24h（§11.2）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SlaService {

    private final SlaInstanceMapper slaInstanceMapper;
    private final SlaPauseMapper slaPauseMapper;
    private final TicketMapper ticketMapper;
    private final WorkCalendarService workCalendarService;
    private final NotificationService notificationService;
    private final ExceptionQueueService exceptionQueueService;

    /**
     * 完成 SLA 目标（工作秒），按优先级（§11.1）：
     * HIGH 高优先级 4 工作小时；MEDIUM 中优先级 1 个工作日(8h)；LOW 低优先级 3 个工作日(24h)。
     */
    public static long targetSeconds(String priority) {
        if (priority == null) priority = "MEDIUM";
        switch (priority) {
            case "HIGH":   return 4 * 3600L;    // 4 工作小时
            case "LOW":    return 24 * 3600L;   // 3 个工作日(8h×3)
            default:       return 8 * 3600L;    // MEDIUM 1 个工作日(8h)
        }
    }

    /**
     * 优先级变化：重算完成 SLA 目标（§11.4 优先级变化后重新计算完成目标）。
     * 保留已消耗工作秒，仅更新目标工作秒与优先级快照。
     */
    @Transactional
    public void onPriorityChanged(String ticketId, String newPriority) {
        SlaInstance sla = runningOrPausedCompletionSla(ticketId);
        if (sla == null) return;
        SlaInstance upd = new SlaInstance();
        upd.setSlaId(sla.getSlaId());
        upd.setPrioritySnapshot(newPriority);
        upd.setTargetWorkSeconds(targetSeconds(newPriority));
        upd.setTargetAt(workCalendarService.addWorkSeconds(sla.getCreatedAt(), targetSeconds(newPriority)));
        upd.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        slaInstanceMapper.updateById(upd);
        log.info("[SLA] 优先级变化重算目标: {} -> {} 目标时刻", ticketId, newPriority, upd.getTargetAt());
    }

    /** 查运行中或暂停中的完成 SLA（优先级重算用） */
    private SlaInstance runningOrPausedCompletionSla(String ticketId) {
        return slaInstanceMapper.selectOne(new QueryWrapper<SlaInstance>()
                .eq("biz_type", "TICKET").eq("biz_id", ticketId).eq("sla_type", "TICKET_COMPLETION")
                .in("status", "RUNNING", "PAUSED").orderByDesc("created_at").last("LIMIT 1"));
    }

    /** 创建完成 SLA（工单创建时调用，§11.2 创建起算） */
    @Transactional
    public SlaInstance startCompletionSla(String ticketId, String priority, LocalDateTime createdAt) {
        SlaInstance sla = new SlaInstance();
        sla.setSlaId("SLA" + UUID.randomUUID().toString().replace("-", "").substring(0, 29));
        sla.setTicketId(ticketId);
        sla.setBizType("TICKET");
        sla.setBizId(ticketId);
        sla.setSlaType("TICKET_COMPLETION");
        sla.setPrioritySnapshot(priority);
        sla.setTargetWorkSeconds(targetSeconds(priority));
        sla.setCalendarId(workCalendarService.calendarId());
        sla.setCalendarVersion(workCalendarService.calendarVersion());
        sla.setVersion(0L);
        sla.setTargetAt(workCalendarService.addWorkSeconds(createdAt != null ? createdAt : LocalDateTime.now(java.time.ZoneOffset.UTC), targetSeconds(priority)));
        sla.setElapsedWorkSeconds(0L);
        sla.setPausedSeconds(0L);
        sla.setNearBreachNotified(0);
        sla.setStatus("RUNNING");
        sla.setCreatedAt(createdAt != null ? createdAt : LocalDateTime.now(java.time.ZoneOffset.UTC));
        sla.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        slaInstanceMapper.insert(sla);
        return sla;
    }

    /** 暂停完成 SLA（进入补充/外部等待，§11.3） */
    @Transactional
    public void pause(String ticketId, String reasonType, String operatorId) {
        SlaInstance sla = runningCompletionSla(ticketId);
        if (sla == null) return;
        SlaPause pause = new SlaPause();
        pause.setPauseId("PS" + UUID.randomUUID().toString().replace("-", "").substring(0, 30));
        pause.setSlaId(sla.getSlaId());
        pause.setReasonType(reasonType);
        pause.setStartedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        pause.setOperatorId(operatorId);
        pause.setCreatedAt(pause.getStartedAt());
        pause.setUpdatedAt(pause.getStartedAt());
        slaPauseMapper.insert(pause);
        SlaInstance upd = new SlaInstance();
        upd.setSlaId(sla.getSlaId());
        upd.setStatus("PAUSED");
        upd.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        slaInstanceMapper.updateById(upd);
    }

    /** 恢复完成 SLA（补充提交/外部恢复，§11.3） */
    @Transactional
    public void resume(String ticketId, String operatorId) {
        SlaInstance sla = pausedCompletionSla(ticketId);
        if (sla == null) {
            sla = slaInstanceMapper.selectOne(new QueryWrapper<SlaInstance>()
                    .eq("biz_type", "TICKET").eq("biz_id", ticketId).eq("sla_type", "TICKET_COMPLETION")
                    .eq("status", "MET").last("LIMIT 1"));
            if (sla == null) return;
            LocalDateTime now = LocalDateTime.now(java.time.ZoneOffset.UTC);
            long waiting = workCalendarService.workSecondsBetween(sla.getMetAt(), now);
            SlaInstance resumed = new SlaInstance();
            resumed.setSlaId(sla.getSlaId()); resumed.setStatus("RUNNING");
            resumed.setPausedSeconds((sla.getPausedSeconds() == null ? 0 : sla.getPausedSeconds()) + waiting);
            resumed.setTargetAt(workCalendarService.addWorkSeconds(sla.getTargetAt(), waiting));
            resumed.setUpdatedAt(now);
            slaInstanceMapper.updateById(resumed);
            return;
        }
        List<SlaPause> open = slaPauseMapper.selectList(new QueryWrapper<SlaPause>()
                .eq("sla_id", sla.getSlaId()).isNull("ended_at"));
        long pauseSeconds = 0;
        LocalDateTime now = LocalDateTime.now(java.time.ZoneOffset.UTC);
        for (SlaPause p : open) {
            p.setEndedAt(now);
            p.setUpdatedAt(now);
            slaPauseMapper.updateById(p);
            pauseSeconds += workCalendarService.workSecondsBetween(p.getStartedAt(), now);
        }
        SlaInstance upd = new SlaInstance();
        upd.setSlaId(sla.getSlaId());
        upd.setStatus("RUNNING");
        upd.setPausedSeconds((sla.getPausedSeconds() == null ? 0 : sla.getPausedSeconds()) + pauseSeconds);
        upd.setTargetAt(workCalendarService.addWorkSeconds(sla.getTargetAt(), pauseSeconds));
        upd.setUpdatedAt(now);
        slaInstanceMapper.updateById(upd);
    }

    /** 停止完成 SLA（终态或进入验收阶段，§11.4） */
    @Transactional
    public void stop(String ticketId) {
        SlaInstance sla = runningCompletionSla(ticketId);
        if (sla == null) sla = pausedCompletionSla(ticketId);
        if (sla == null) return;
        SlaInstance upd = new SlaInstance();
        upd.setSlaId(sla.getSlaId());
        upd.setStatus("MET");
        upd.setMetAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        upd.setUpdatedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        slaInstanceMapper.updateById(upd);
    }

    @Transactional
    public void cancel(String ticketId) {
        slaInstanceMapper.update(null, new com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper<SlaInstance>()
                .eq("biz_type", "TICKET").eq("biz_id", ticketId)
                .in("sla_type", "TICKET_COMPLETION", "TICKET_RESPONSE")
                .set("status", "CANCELLED").set("updated_at", LocalDateTime.now(java.time.ZoneOffset.UTC)));
    }

    private SlaInstance runningCompletionSla(String ticketId) {
        return slaInstanceMapper.selectOne(new QueryWrapper<SlaInstance>()
                .eq("biz_type", "TICKET").eq("biz_id", ticketId).eq("sla_type", "TICKET_COMPLETION").eq("status", "RUNNING").last("limit 1"));
    }

    private SlaInstance pausedCompletionSla(String ticketId) {
        return slaInstanceMapper.selectOne(new QueryWrapper<SlaInstance>()
                .eq("biz_type", "TICKET").eq("biz_id", ticketId).eq("sla_type", "TICKET_COMPLETION").eq("status", "PAUSED").last("limit 1"));
    }

    /** SLA 扫描（每 1 分钟）：推进计时 → 80% 提醒 → 违约标记+通知+异常队列 */
    @Scheduled(fixedDelay = 60000, initialDelay = 30000)
    @Transactional
    public void scan() {
        List<SlaInstance> running = slaInstanceMapper.selectList(new QueryWrapper<SlaInstance>()
                .eq("biz_type", "TICKET").eq("sla_type", "TICKET_COMPLETION").eq("status", "RUNNING"));
        if (running.isEmpty()) return;
        LocalDateTime now = LocalDateTime.now(java.time.ZoneOffset.UTC);
        for (SlaInstance sla : running) {
            try {
                processOne(sla, now);
            } catch (Exception e) {
                log.error("[SLA] 扫描处理异常: " + sla.getSlaId(), e);
            }
        }
    }

    private void processOne(SlaInstance sla, LocalDateTime now) {
        // 与撤回采用相同锁顺序：工单 → SLA。扫描快照可能早于撤回，必须重新读取。
        Ticket currentTicket = ticketMapper.selectOne(new QueryWrapper<Ticket>()
                .eq("ticket_id", sla.getBizId()).last("FOR UPDATE"));
        if (currentTicket == null || currentTicket.getStatus() == null || currentTicket.getStatus().isTerminal()) return;
        sla = slaInstanceMapper.selectOne(new QueryWrapper<SlaInstance>()
                .eq("sla_id", sla.getSlaId()).eq("status", "RUNNING").last("FOR UPDATE"));
        if (sla == null || !"RUNNING".equals(sla.getStatus())) return;
        long elapsed = workCalendarService.workSecondsBetween(sla.getCreatedAt(), now);
        long paused = sla.getPausedSeconds() == null ? 0 : sla.getPausedSeconds();
        long effective = elapsed - paused;
        if (effective < 0) effective = 0;
        LocalDateTime targetAt = sla.getTargetAt();
        if (targetAt == null) return; // 无目标时刻（历史数据）跳过
        long target = sla.getTargetWorkSeconds() == null ? workCalendarService.workSecondsBetween(sla.getCreatedAt(), targetAt) : sla.getTargetWorkSeconds();
        double ratio = target > 0 ? (double) effective / target : 0;

        // 违约（§11.2）
        if (!now.isBefore(targetAt) && sla.getBreachAt() == null) {
            SlaInstance upd = new SlaInstance();
            upd.setSlaId(sla.getSlaId());
            upd.setStatus("BREACHED");
            upd.setBreachAt(now); // breach_at 写入后不可删除
            upd.setElapsedWorkSeconds(effective);
            upd.setUpdatedAt(now);
            slaInstanceMapper.updateById(upd);
            Ticket ticket = ticketMapper.selectById(sla.getTicketId());
            if (ticket != null && ticket.getAssigneeId() != null) {
                notificationService.sendInbox("SLA_BREACHED:" + sla.getTicketId(), ticket.getAssigneeId(),
                        "SLA 违约", "工单【" + ticket.getTitle() + "】已完成 SLA 违约",
                        "/tickets/" + ticket.getTicketId());
            }
            exceptionQueueService.raise("TICKET", sla.getTicketId(), ExceptionQueueService.TYPE_LONG_PENDING,
                    "SLA 违约", "工单完成 SLA 违约（优先级 " + sla.getPrioritySnapshot() + "）", sla.getPrioritySnapshot());
            return;
        }

        // 80% 临近违约提醒（仅一次，§11.5）
        if (ratio >= 0.8 && (sla.getNearBreachNotified() == null || sla.getNearBreachNotified() == 0)) {
            Ticket ticket = ticketMapper.selectById(sla.getTicketId());
            if (ticket != null && ticket.getAssigneeId() != null) {
                notificationService.sendInbox("SLA_NEAR:" + sla.getTicketId(), ticket.getAssigneeId(),
                        "SLA 临近违约", "工单【" + ticket.getTitle() + "】已完成 80% 的 SLA 目标，请尽快处理",
                        "/tickets/" + ticket.getTicketId());
            }
            SlaInstance upd = new SlaInstance();
            upd.setSlaId(sla.getSlaId());
            upd.setNearBreachNotified(1);
            upd.setElapsedWorkSeconds(effective);
            upd.setUpdatedAt(now);
            slaInstanceMapper.updateById(upd);
            return;
        }

        // 常规推进：持久化累计（供报表）
        long old = sla.getElapsedWorkSeconds() == null ? 0 : sla.getElapsedWorkSeconds();
        if (effective != old) {
            SlaInstance upd = new SlaInstance();
            upd.setSlaId(sla.getSlaId());
            upd.setElapsedWorkSeconds(effective);
            upd.setUpdatedAt(now);
            slaInstanceMapper.updateById(upd);
        }
    }
}
