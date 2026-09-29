package com.itticket.consultation.api;

import lombok.Getter;

/**
 * 统一响应码(PRD 21.3 核心错误码 + AI-006 AI 领域错误码)。
 *
 * <p>字符串码是对外契约的一部分,不得复用为其他语义。
 * {@code INTERNAL_ERROR} 是平台兜底码,不表达任何业务规则。
 */
@Getter
public enum ApiCode {

    SUCCESS("success", 200),

    VALIDATION_ERROR("request validation failed", 400),
    UNAUTHENTICATED("unauthenticated", 401),
    FORBIDDEN("forbidden", 403),
    OBJECT_NOT_FOUND("object not found", 404),
    ILLEGAL_STATE_TRANSITION("illegal state transition", 409),
    IDEMPOTENCY_CONFLICT("idempotency key conflict", 409),
    ASSIGNMENT_CHANGED("assignment changed", 409),
    /** 超过消息撤回时限(PRD 21.3 / 13.2 的 5 分钟窗口)。 */
    WITHDRAW_WINDOW_EXPIRED("withdraw window expired", 409),
    /** 服务日历或 SLA 配置非法,例如工作时段重叠或逆序(AX-002)。 */
    SLA_CONFIG_INVALID("sla configuration invalid", 409),

    /** AI 依赖不可用。响应必须给出转人工/提单入口(AI-006 fallback)。 */
    AI_UNAVAILABLE("AI service unavailable", 503),
    /** 模型输出不满足 AI-004 Schema。默认策略不外抛,降级为结构化拒答并记录该分类。 */
    AI_SCHEMA_INVALID("AI response schema invalid", 502),
    /** 无可靠知识。默认策略以 REFUSE 回复表达,保留该码用于强错误模式。 */
    AI_NO_RELIABLE_KNOWLEDGE("no reliable knowledge", 422),
    /** 高风险主题被拦截。默认策略以 REFUSE 回复表达,保留该码用于强错误模式。 */
    AI_HIGH_RISK_BLOCKED("high risk topic blocked", 422),
    /** 会话不处于允许 AI 交互的状态。 */
    AI_SESSION_NOT_ACTIVE("consultation session is not active for AI", 409),

    INTERNAL_ERROR("internal error", 500);

    private final String defaultMessage;
    private final int httpStatus;

    ApiCode(String defaultMessage, int httpStatus) {
        this.defaultMessage = defaultMessage;
        this.httpStatus = httpStatus;
    }
}
