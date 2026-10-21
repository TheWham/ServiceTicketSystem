package com.itticket.ticket.service;

/**
 * 自动路由的产出结果 —— 显式区分三种结局，不用 null 兼表多义。
 *
 * <p>AGENTS.md 要求「明确区分失败、正常空结果与业务拒绝」，此前 {@code route()} 返回
 * {@code String} 且以 null 同时表示「路由失败」与「工单已终态」；改为派单草案后
 * null 还要再兼表「已挂起待确认」，必须换成可判别的结果对象。
 *
 * @param kind       结局类型
 * @param engineerId 候选工程师（{@link Kind#DRAFT_PENDING} 时非空）
 * @param draftId    派单草案 ID（{@link Kind#DRAFT_PENDING} 时非空）
 */
public record RouteOutcome(Kind kind, String engineerId, String draftId) {

    /** 路由结局。 */
    public enum Kind {
        /** 已产出派单草案，工单保持 NEW 待人工确认 —— 正常路径。 */
        DRAFT_PENDING,
        /** 无候选工程师，已入异常队列并通知管理员 —— 失败。 */
        ROUTE_FAILED,
        /** 工单不存在或已终态，无需路由 —— 正常空结果，非失败。 */
        SKIPPED
    }

    public static RouteOutcome draftPending(String engineerId, String draftId) {
        return new RouteOutcome(Kind.DRAFT_PENDING, engineerId, draftId);
    }

    public static RouteOutcome routeFailed() {
        return new RouteOutcome(Kind.ROUTE_FAILED, null, null);
    }

    public static RouteOutcome skipped() {
        return new RouteOutcome(Kind.SKIPPED, null, null);
    }
}
