package com.itticket.consultation.service;

import com.itticket.consultation.enums.ConsultationResolutionType;
import com.itticket.consultation.statemachine.ConsultationEvent;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 一次咨询状态迁移的完整意图。
 *
 * <p>只允许描述 SM-CONSULT-001 副作用列真正需要改写的投影字段:责任人、解决方式、
 * 关联工单和关闭时间。目标状态由状态机推导,调用方不能指定(SM-001 禁止绕过动作白名单)。
 */
@Getter
@Builder
public class TransitionSpec {

    private final ConsultationEvent event;
    private final CurrentUser actor;
    /** 审计原因。关闭、恢复等动作必填。 */
    private final String reason;

    /** 是否改写 category_id;转人工时员工确认的咨询分类(PRD 8.4)。 */
    @Builder.Default
    private final boolean setCategoryId = false;
    private final String categoryId;

    /** 是否改写 current_engineer_id;转人工设为新责任人。 */
    @Builder.Default
    private final boolean setEngineer = false;
    private final String engineerId;

    @Builder.Default
    private final boolean setResolutionType = false;
    private final ConsultationResolutionType resolutionType;

    @Builder.Default
    private final boolean setConvertedTicketId = false;
    private final String convertedTicketId;

    @Builder.Default
    private final boolean setClosedAt = false;
    private final LocalDateTime closedAt;

    /** EV-008 规定的最小事件 payload;事件类型由 event.domainEventType 决定。 */
    private final Map<String, Object> eventPayload;

    /**
     * 是否推迟发事件,由编排层在拿齐 payload 后自行写 Outbox。
     *
     * <p>用于 CONSULTATION_TRANSFERRED:EV-008 把 assignment_id 列为必填,
     * 而分配发生在状态迁移之后,迁移那一刻构造不出合法 payload。
     */
    @Builder.Default
    private final boolean deferEvent = false;
}
