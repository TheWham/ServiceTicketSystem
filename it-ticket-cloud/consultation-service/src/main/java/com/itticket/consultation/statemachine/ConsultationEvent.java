package com.itticket.consultation.statemachine;

import lombok.Getter;

/**
 * 咨询业务动作码(SM-001:稳定的 DOMAIN_ACTION 形式,一经发布不得复用为其他语义)。
 *
 * <p>{@code domainEventType} 是该动作在 SM-EVENT-001 最小事件集合中对应的领域事实事件类型;
 * 为 null 表示该动作不在最小集合内,不产生 Outbox 事件。
 */
@Getter
public enum ConsultationEvent {

    /** 起点:开始 AI 咨询。 */
    CONSULTATION_START_AI(null),
    /** 起点:跳过 AI 直接转人工,创建人工分配任务。 */
    CONSULTATION_START_HUMAN("CONSULTATION_TRANSFERRED"),
    /** AI_ACTIVE:转人工。 */
    CONSULTATION_TRANSFER("CONSULTATION_TRANSFERRED"),
    /** WAITING_ENGINEER:工程师首次有效回复。 */
    CONSULTATION_RESPOND("CONSULTATION_RESPONDED"),
    /** HUMAN_ACTIVE:工程师提交解决结论。 */
    CONSULTATION_SUBMIT_RESOLUTION(null),
    /** PENDING_CONFIRMATION:员工确认解决。 */
    CONSULTATION_CONFIRM_RESOLVED("CONSULTATION_RESOLVED"),
    /** PENDING_CONFIRMATION:断开且 10 分钟无回复,系统自动解决。 */
    CONSULTATION_AUTO_RESOLVE("CONSULTATION_RESOLVED"),
    /** PENDING_CONFIRMATION:员工回复未解决,退回人工处理。 */
    CONSULTATION_REJECT_RESOLUTION(null),
    /** 任意非终态:确认创建工单。 */
    CONSULTATION_CONVERT("CONSULTATION_CONVERTED"),
    /** 任意非终态:员工主动结束。 */
    CONSULTATION_CLOSE(null),
    /** RESOLVED:24 小时内恢复。 */
    CONSULTATION_REOPEN("CONSULTATION_REOPENED");

    private final String domainEventType;

    ConsultationEvent(String domainEventType) {
        this.domainEventType = domainEventType;
    }

    public boolean producesDomainEvent() {
        return domainEventType != null;
    }
}
