package com.itticket.consultation.scheduler;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.ConsultationResolutionType;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.mapper.ConsultationMapper;
import com.itticket.consultation.mapper.ConsultationMessageMapper;
import com.itticket.consultation.service.ConsultationService;
import com.itticket.consultation.service.CurrentUser;
import com.itticket.consultation.service.EmployeePresenceProvider;
import com.itticket.consultation.statemachine.ConsultationEvent;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 咨询自动解决(SM-CONSULT-001 的"断开且 10 分钟无回复" → RESOLVED)。
 *
 * <p>PRD 8.3 给的是合取条件,三者必须同时成立:
 * <ol>
 *   <li>工程师已提交解决结论 —— 即状态已经是 PENDING_CONFIRMATION;</li>
 *   <li>员工会话已断开 —— 由 {@link EmployeePresenceProvider} 提供;</li>
 *   <li>员工 10 分钟内未回复 —— 以最后一条员工消息时间判定。</li>
 * </ol>
 * PRD 同时明确"不得仅因普通对话连续 10 分钟无消息而自动判定解决",
 * 所以第 2 条不可省略。一期没有员工在线状态来源,默认实现恒返回未断开,
 * 本调度器因此不会触发任何自动解决 —— 这是有意的保守行为,不是遗漏。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ConsultationAutoResolveScheduler {

    private static final int BATCH_SIZE = 50;

    private final ConsultationMapper consultationMapper;
    private final ConsultationMessageMapper messageMapper;
    private final ConsultationService consultationService;
    private final EmployeePresenceProvider presenceProvider;
    private final ConsultationProperties properties;
    private final TransactionTemplate transactionTemplate;

    @Scheduled(fixedDelayString = "${itticket.consultation.scheduler.auto-resolve-delay-ms:60000}")
    public void scan() {
        RequestContext.set("sys_" + UUID.randomUUID().toString().replace("-", ""));
        try {
            LocalDateTime now = Times.nowUtc();
            LocalDateTime idleBefore = now.minusMinutes(
                    properties.getLifecycle().getAutoResolveIdleMinutes());

            List<Consultation> candidates = consultationMapper.selectList(
                    Wrappers.<Consultation>lambdaQuery()
                            .eq(Consultation::getStatus, ConsultationStatus.PENDING_CONFIRMATION)
                            .le(Consultation::getUpdatedAt, idleBefore)
                            .orderByAsc(Consultation::getUpdatedAt)
                            .last("LIMIT " + BATCH_SIZE));

            for (Consultation consultation : candidates) {
                try {
                    transactionTemplate.executeWithoutResult(
                            status -> tryAutoResolve(consultation, idleBefore));
                } catch (RuntimeException e) {
                    log.error("[auto-resolve] 处理失败 sessionId={}", consultation.getSessionId(), e);
                }
            }
        } finally {
            RequestContext.clear();
        }
    }

    private void tryAutoResolve(Consultation consultation, LocalDateTime idleBefore) {
        if (!presenceProvider.isDisconnected(consultation.getCreatorId(), consultation.getSessionId())) {
            return;
        }
        if (employeeRepliedAfter(consultation.getSessionId(), idleBefore)) {
            return;
        }
        // 事务内重读,保证守卫基于最新状态与版本(SM-001)
        Consultation current = consultationMapper.selectById(consultation.getSessionId());
        if (current == null || current.getStatus() != ConsultationStatus.PENDING_CONFIRMATION) {
            return;
        }
        consultationService.resolve(current, CurrentUser.system(),
                ConsultationResolutionType.AUTO_RESOLVED,
                ConsultationEvent.CONSULTATION_AUTO_RESOLVE,
                "员工已断开且超过自动解决静默时长");
        log.info("[auto-resolve] 咨询 {} 自动判定已解决", current.getSessionId());
    }

    /** 判定窗口内是否有员工消息;只看员工发的实际消息,AI 与系统消息不计。 */
    private boolean employeeRepliedAfter(String sessionId, LocalDateTime since) {
        Long count = messageMapper.selectCount(Wrappers.<ConsultationMessage>lambdaQuery()
                .eq(ConsultationMessage::getSessionId, sessionId)
                .eq(ConsultationMessage::getSenderType, MessageSenderType.EMPLOYEE)
                .gt(ConsultationMessage::getSentAt, since));
        return count != null && count > 0;
    }
}
