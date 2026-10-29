package com.itticket.ticket.service;

/**
 * 自动路由的产出结果 —— 显式区分各种结局，不用 null 兼表多义。
 *
 * <p>AGENTS.md 要求「明确区分失败、正常空结果与业务拒绝」，此前 {@code route()} 返回
 * {@code String} 且以 null 同时表示「路由失败」与「工单已终态」；改为派单草案后
 * null 还要再兼表「已挂起待确认」，必须换成可判别的结果对象。
 *
 * @param kind       结局类型
 * @param engineerId 工程师（{@link Kind#ASSIGNED} 为被分派人；{@link Kind#DRAFT_PENDING}
 *                   为候选工程师）
 * @param draftId    派单草案 ID（仅 {@link Kind#DRAFT_PENDING} 时非空）
 */
public record RouteOutcome(Kind kind, String engineerId, String draftId) {

    /** 路由结局。 */
    public enum Kind {
        /** 已直接分派，工单进入 ASSIGNED 等待工程师接单 —— 正常路径。 */
        ASSIGNED,
        /**
         * 已产出派单草案，工单保持 NEW 待人工确认。
         *
         * <p><b>当前无生产者</b>：2026-10-27 起 {@code RoutingService.route()} 改为直派，
         * 不再挂草案。保留该取值是因为 {@code TicketMergeIntegrationTest} 仍以
         * {@link #draftPending} 作桩，且整套草案机制（表/控制器/审批页）尚在。
         */
        DRAFT_PENDING,
        /** 无候选工程师，已入异常队列并通知管理员 —— 失败。 */
        ROUTE_FAILED,
        /** 工单不存在、已终态或已分派，无需路由 —— 正常空结果，非失败。 */
        SKIPPED
    }

    public static RouteOutcome assigned(String engineerId) {
        return new RouteOutcome(Kind.ASSIGNED, engineerId, null);
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
