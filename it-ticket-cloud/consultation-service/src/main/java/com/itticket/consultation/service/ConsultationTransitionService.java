package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.mapper.ConsultationMapper;
import com.itticket.consultation.statemachine.ConsultationEvent;
import com.itticket.consultation.statemachine.TransitionDecision;
import com.itticket.consultation.statemachine.ConsultationStateMachine;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 咨询状态迁移的统一执行点(SM-001 迁移执行公约)。
 *
 * <p>每次迁移在同一事务内完成:校验当前状态、操作者角色、对象归属和乐观锁版本 →
 * 写主对象投影 → 写审计 → 写 Outbox。通知、SLA 和案例池是副作用,
 * 不得反向决定迁移是否合法,因此都在本方法返回后由编排层处理。
 *
 * <p>调用方必须已经完成对象归属校验({@link AuthzService});本类只做状态与角色守卫。
 */
@Service
@RequiredArgsConstructor
public class ConsultationTransitionService {

    private static final String ACTOR_TYPE_SYSTEM = "SYSTEM";
    private static final String ACTOR_TYPE_USER = "USER";

    private final ConsultationMapper consultationMapper;
    private final AuditService auditService;
    private final OutboxService outboxService;

    public Consultation load(String sessionId) {
        Consultation consultation = consultationMapper.selectById(sessionId);
        if (consultation == null) {
            throw ApiException.notFound();
        }
        return consultation;
    }

    /** 仅在写事务内调用：锁住会话，串行化关闭和消息落库，使用最新已提交状态。 */
    public Consultation loadForUpdate(String sessionId) {
        Consultation consultation = consultationMapper.selectOne(Wrappers.<Consultation>lambdaQuery()
                .eq(Consultation::getSessionId, sessionId).last("FOR UPDATE"));
        if (consultation == null) throw ApiException.notFound();
        return consultation;
    }

    /**
     * 执行一次迁移。
     *
     * @return 迁移后的最新投影
     * @throws ApiException ILLEGAL_STATE_TRANSITION / FORBIDDEN / ASSIGNMENT_CHANGED(SM-001)
     */
    public Consultation apply(Consultation current, TransitionSpec spec) {
        ConsultationEvent event = spec.getEvent();
        TransitionDecision decision = ConsultationStateMachine.evaluate(
                current.getStatus(), event, spec.getActor().actor());
        if (!decision.allowed()) {
            throw new ApiException(decision.failureCode(), decision.message());
        }

        LocalDateTime now = Times.nowUtc();
        long nextVersion = current.getVersion() + 1;
        ConsultationStatus target = decision.to();

        LambdaUpdateWrapper<Consultation> update = Wrappers.<Consultation>lambdaUpdate()
                .eq(Consultation::getSessionId, current.getSessionId())
                // DM-001:更新必须把 version 放入 WHERE 条件并递增
                .eq(Consultation::getVersion, current.getVersion())
                .set(Consultation::getStatus, target)
                .set(Consultation::getVersion, nextVersion)
                .set(Consultation::getUpdatedAt, now);
        if (spec.isSetCategoryId()) {
            update.set(Consultation::getCategoryId, spec.getCategoryId());
        }
        if (spec.isSetEngineer()) {
            update.set(Consultation::getCurrentEngineerId, spec.getEngineerId());
        }
        if (spec.isSetResolutionType()) {
            update.set(Consultation::getResolutionType, spec.getResolutionType());
        }
        if (spec.isSetConvertedTicketId()) {
            update.set(Consultation::getConvertedTicketId, spec.getConvertedTicketId());
        }
        if (spec.isSetClosedAt()) {
            update.set(Consultation::getClosedAt, spec.getClosedAt());
        }

        int rows = consultationMapper.update(null, update);
        if (rows == 0) {
            // 乐观锁失败:重新读取后返回明确错误,不盲目重试(RD-001 业务冲突)
            throw new ApiException(ApiCode.ASSIGNMENT_CHANGED, "咨询已被其他操作变更,请重新读取后再试");
        }

        Consultation after = consultationMapper.selectById(current.getSessionId());
        writeAudit(current, after, event, spec);
        writeEvent(after, event, spec, nextVersion);
        return after;
    }

    private void writeAudit(Consultation before, Consultation after,
                            ConsultationEvent event, TransitionSpec spec) {
        auditService.record(
                spec.getActor().userId(),
                event.name(),
                AuditService.OBJECT_CONSULTATION,
                after.getSessionId(),
                projection(before),
                projection(after),
                spec.getReason());
    }

    private void writeEvent(Consultation after, ConsultationEvent event,
                            TransitionSpec spec, long aggregateVersion) {
        if (!event.producesDomainEvent() || spec.isDeferEvent()) {
            return;
        }
        Map<String, Object> payload = spec.getEventPayload() == null
                ? Map.of("session_id", after.getSessionId())
                : spec.getEventPayload();
        String actorType = spec.getActor().actor() == com.itticket.consultation.statemachine.Actor.SYSTEM
                ? ACTOR_TYPE_SYSTEM : ACTOR_TYPE_USER;
        outboxService.appendConsultation(event.getDomainEventType(), after.getSessionId(),
                aggregateVersion, payload, actorType, spec.getActor().userId());
    }

    /** 审计只记录状态投影字段,不含聊天正文(RD-013)。 */
    private Map<String, Object> projection(Consultation consultation) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("status", consultation.getStatus() == null ? null : consultation.getStatus().getValue());
        map.put("current_engineer_id", consultation.getCurrentEngineerId());
        map.put("category_id", consultation.getCategoryId());
        map.put("resolved_type", consultation.getResolutionType() == null
                ? null : consultation.getResolutionType().getValue());
        map.put("converted_ticket_id", consultation.getConvertedTicketId());
        map.put("version", consultation.getVersion());
        return map;
    }
}
