package com.itticket.consultation.api;

/**
 * 请求级追踪上下文(RD-010:每个请求、事件、任务必须携带 requestId/traceId)。
 * 调度任务在入口显式 {@link #set(String)} 一个系统 requestId。
 */
public final class RequestContext {

    private static final ThreadLocal<String> REQUEST_ID = new ThreadLocal<>();

    private RequestContext() {
    }

    public static void set(String requestId) {
        REQUEST_ID.set(requestId);
    }

    /** 未设置时返回占位串,保证审计与事件的 request_id 列非空。 */
    public static String get() {
        String value = REQUEST_ID.get();
        return value == null ? "req_unset" : value;
    }

    public static void clear() {
        REQUEST_ID.remove();
    }
}
