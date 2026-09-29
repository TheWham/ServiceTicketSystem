package com.itticket.consultation.statemachine;

import com.itticket.consultation.enums.ConsultationStatus;

import java.util.Set;

/**
 * SM-CONSULT-001 迁移表的一行。
 *
 * @param from  当前状态;null 表示"起点"(尚不存在会话)
 * @param event 业务动作码
 * @param to    目标状态
 * @param actors 允许执行该动作的操作者类别
 */
public record TransitionRule(ConsultationStatus from,
                             ConsultationEvent event,
                             ConsultationStatus to,
                             Set<Actor> actors) {

    static TransitionRule of(ConsultationStatus from, ConsultationEvent event,
                             ConsultationStatus to, Actor... actors) {
        return new TransitionRule(from, event, to, Set.of(actors));
    }
}
