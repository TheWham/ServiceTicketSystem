package com.itticket.ai.enums;

/**
 * 咨询会话状态机:
 * AI_HANDLING(AI解答中) ──员工确认解决──→ RESOLVED
 *     │                                   员工直接结束 → CLOSED
 *     ├──员工点"未解决"或AI判定无法解决──→ WAITING_HUMAN(排队等客服)
 * WAITING_HUMAN ──客服接入──→ HUMAN_HANDLING(人工沟通中)
 * HUMAN_HANDLING ──客服标记解决──→ RESOLVED
 *                ──客服转工单──→ TO_TICKET
 *                ──客服驳回(重复/无效/已解决)──→ REJECTED
 * REJECTED 允许员工再次发起(新建会话,不复活旧会话)
 */
public enum SessionStatus {
    /** AI 解答中 */
    AI_HANDLING,
    /** 排队等待人工客服 */
    WAITING_HUMAN,
    /** 人工客服沟通中 */
    HUMAN_HANDLING,
    /** 已解决(AI 或人工确认) */
    RESOLVED,
    /** 已转工单 */
    TO_TICKET,
    /** 客服驳回 */
    REJECTED,
    /** 员工直接结束 */
    CLOSED
}
