package com.itticket.consultation.statemachine;

import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.enums.ConsultationStatus;

/**
 * 守卫判定结果。
 *
 * <p>SM-001:守卫失败返回 ILLEGAL_STATE_TRANSITION、FORBIDDEN 或 ASSIGNMENT_CHANGED。
 * 本判定只负责前两者;责任人变化由服务层在同一事务内比对后返回 ASSIGNMENT_CHANGED。
 */
public record TransitionDecision(boolean allowed,
                                 ConsultationStatus to,
                                 ApiCode failureCode,
                                 String message) {

    static TransitionDecision allow(ConsultationStatus to) {
        return new TransitionDecision(true, to, null, null);
    }

    static TransitionDecision deny(ApiCode code, String message) {
        return new TransitionDecision(false, null, code, message);
    }
}
