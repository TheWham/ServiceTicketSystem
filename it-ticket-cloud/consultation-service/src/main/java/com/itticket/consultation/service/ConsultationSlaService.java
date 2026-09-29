package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.entity.SlaInstance;
import com.itticket.consultation.enums.AssignmentBizType;
import com.itticket.consultation.enums.SlaStatus;
import com.itticket.consultation.enums.SlaType;
import com.itticket.consultation.mapper.SlaInstanceMapper;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

/**
 * 咨询响应 SLA(PRD 11.2 默认 10 个工作分钟 / AX-002)。
 *
 * <p>一个咨询在 (CONSULTATION, sessionId, CONSULTATION_RESPONSE) 上只有一条投影行。
 * 关键约束:
 * <ul>
 *   <li>违约一经产生不可通过后续操作删除(PRD 11.2),因此 {@code breachedAt} 一旦写入就不再清空,
 *       恢复咨询时只重置目标和状态;</li>
 *   <li>候选人之间的自动转派不重置本投影(RD-005),下一候选人的计时由
 *       {@code assignment.response_deadline} 承载;</li>
 *   <li>计时只能用服务日历,不能用客户端时间(RD-004)。</li>
 * </ul>
 */
@Service
@RequiredArgsConstructor
public class ConsultationSlaService {

    private final SlaInstanceMapper slaInstanceMapper;
    private final ServiceCalendarProvider calendarProvider;
    private final ConsultationProperties properties;

    /** 转人工或恢复咨询时启动/重启响应 SLA。 */
    public SlaInstance startOrRestart(String sessionId, LocalDateTime startAt) {
        WorkCalendar calendar = calendarProvider.current();
        long target = properties.getSla().getResponseTargetWorkSeconds();
        LocalDateTime targetAt = calendar.deadlineUtc(startAt, target);
        LocalDateTime now = Times.nowUtc();

        SlaInstance existing = find(sessionId);
        if (existing == null) {
            SlaInstance instance = new SlaInstance();
            instance.setSlaId(Ids.slaId());
            instance.setBizType(AssignmentBizType.CONSULTATION);
            instance.setBizId(sessionId);
            instance.setSlaType(SlaType.CONSULTATION_RESPONSE);
            instance.setStatus(SlaStatus.RUNNING);
            instance.setTargetWorkSeconds(target);
            instance.setElapsedWorkSeconds(0L);
            instance.setPausedSeconds(0L);
            instance.setTargetAt(targetAt);
            instance.setCalendarId(calendar.calendarId());
            instance.setCalendarVersion(calendar.version());
            instance.setVersion(0L);
            instance.setCreatedAt(now);
            instance.setUpdatedAt(now);
            slaInstanceMapper.insert(instance);
            return instance;
        }

        // 恢复咨询:PRD 8.3 明确"重新启动 10 个工作分钟响应 SLA"。breachedAt 保留不清。
        slaInstanceMapper.update(null, Wrappers.<SlaInstance>lambdaUpdate()
                .eq(SlaInstance::getSlaId, existing.getSlaId())
                .eq(SlaInstance::getVersion, existing.getVersion())
                .set(SlaInstance::getStatus, SlaStatus.RUNNING)
                .set(SlaInstance::getTargetWorkSeconds, target)
                .set(SlaInstance::getElapsedWorkSeconds, 0L)
                .set(SlaInstance::getTargetAt, targetAt)
                .set(SlaInstance::getMetAt, null)
                .set(SlaInstance::getCalendarId, calendar.calendarId())
                .set(SlaInstance::getCalendarVersion, calendar.version())
                .set(SlaInstance::getVersion, existing.getVersion() + 1)
                .set(SlaInstance::getUpdatedAt, now));
        return find(sessionId);
    }

    /**
     * 工程师首次有效回复达成响应目标。
     * 已违约的投影保留 BREACHED 状态,只补记 metAt,避免用后续操作抹掉违约事实。
     */
    public void markResponded(String sessionId, LocalDateTime startedAt, LocalDateTime respondedAt) {
        SlaInstance existing = find(sessionId);
        if (existing == null) {
            return;
        }
        WorkCalendar calendar = calendarProvider.current();
        // AX-002:响应 SLA 在有效分配时启动,因此耗时从当前分配任务的 assignedAt 起算。
        // sla_instance 没有独立的 started_at 列(SQL-010 未定义),用投影创建时间兜底。
        LocalDateTime from = startedAt == null ? existing.getCreatedAt() : startedAt;
        long elapsed = calendar.elapsedWorkSeconds(from, respondedAt);
        SlaStatus next = existing.getStatus() == SlaStatus.RUNNING ? SlaStatus.MET : existing.getStatus();

        slaInstanceMapper.update(null, Wrappers.<SlaInstance>lambdaUpdate()
                .eq(SlaInstance::getSlaId, existing.getSlaId())
                .eq(SlaInstance::getVersion, existing.getVersion())
                .set(SlaInstance::getStatus, next)
                .set(SlaInstance::getMetAt, respondedAt)
                .set(SlaInstance::getElapsedWorkSeconds, elapsed)
                .set(SlaInstance::getVersion, existing.getVersion() + 1)
                .set(SlaInstance::getUpdatedAt, Times.nowUtc()));
    }

    /** 咨询进入 CLOSED/CONVERTED_TO_TICKET 等终态且从未达成响应时,SLA 取消计时。 */
    public void cancel(String sessionId) {
        SlaInstance existing = find(sessionId);
        if (existing == null || existing.getStatus() != SlaStatus.RUNNING) {
            return;
        }
        slaInstanceMapper.update(null, Wrappers.<SlaInstance>lambdaUpdate()
                .eq(SlaInstance::getSlaId, existing.getSlaId())
                .eq(SlaInstance::getVersion, existing.getVersion())
                .set(SlaInstance::getStatus, SlaStatus.CANCELLED)
                .set(SlaInstance::getVersion, existing.getVersion() + 1)
                .set(SlaInstance::getUpdatedAt, Times.nowUtc()));
    }

    public SlaInstance find(String sessionId) {
        return slaInstanceMapper.selectOne(Wrappers.<SlaInstance>lambdaQuery()
                .eq(SlaInstance::getBizType, AssignmentBizType.CONSULTATION)
                .eq(SlaInstance::getBizId, sessionId)
                .eq(SlaInstance::getSlaType, SlaType.CONSULTATION_RESPONSE));
    }

    /** 扫描仍在计时的响应 SLA,供提醒调度器使用。 */
    public java.util.List<SlaInstance> findRunning(int limit) {
        return slaInstanceMapper.selectList(Wrappers.<SlaInstance>lambdaQuery()
                .eq(SlaInstance::getBizType, AssignmentBizType.CONSULTATION)
                .eq(SlaInstance::getSlaType, SlaType.CONSULTATION_RESPONSE)
                .eq(SlaInstance::getStatus, SlaStatus.RUNNING)
                .orderByAsc(SlaInstance::getTargetAt)
                .last("LIMIT " + limit));
    }

    /** 计算临近超时提醒时刻(PRD 11.3:响应 SLA 在第 8 个工作分钟提醒)。 */
    public LocalDateTime nearBreachAt(LocalDateTime startedAt) {
        return calendarProvider.current()
                .deadlineUtc(startedAt, properties.getSla().getNearBreachWorkSeconds());
    }

    /**
     * 提醒发出前推进 SLA 投影版本。
     *
     * <p>Outbox 的唯一键是 (aggregate_type, aggregate_id, aggregate_version),
     * 因此同一 SLA 的临近超时事件与违约事件必须落在不同版本上,否则后者会被唯一键吞掉。
     * 这里用带 version 条件的更新既推进版本,又充当并发抢占:返回 -1 表示本轮没抢到,
     * 调用方不得发事件。
     */
    public long bumpVersionForReminder(SlaInstance instance) {
        long next = instance.getVersion() + 1;
        int updated = slaInstanceMapper.update(null, Wrappers.<SlaInstance>lambdaUpdate()
                .eq(SlaInstance::getSlaId, instance.getSlaId())
                .eq(SlaInstance::getVersion, instance.getVersion())
                .eq(SlaInstance::getStatus, SlaStatus.RUNNING)
                .set(SlaInstance::getVersion, next)
                .set(SlaInstance::getUpdatedAt, Times.nowUtc()));
        return updated > 0 ? next : -1L;
    }

    /** 供调度器使用:标记违约。返回 true 表示本次调用写入了违约事实。 */
    public boolean markBreached(SlaInstance instance, LocalDateTime breachedAt) {
        int updated = slaInstanceMapper.update(null, Wrappers.<SlaInstance>lambdaUpdate()
                .eq(SlaInstance::getSlaId, instance.getSlaId())
                .eq(SlaInstance::getVersion, instance.getVersion())
                .eq(SlaInstance::getStatus, SlaStatus.RUNNING)
                .set(SlaInstance::getStatus, SlaStatus.BREACHED)
                .set(SlaInstance::getBreachedAt, breachedAt)
                .set(SlaInstance::getVersion, instance.getVersion() + 1)
                .set(SlaInstance::getUpdatedAt, Times.nowUtc()));
        return updated > 0;
    }
}
