package com.itticket.common.api;

import lombok.Getter;

/**
 * 统一错误码 —— 与 Node.js 版 error 码表逐字对齐
 * httpStatus 为该错误应返回的 HTTP 状态码(与旧版 res.status(...) 保持一致)
 */
@Getter
public enum ErrorCode {
    PARAM_INVALID(40001, "参数校验失败", 400),
    ASSIGNEE_INVALID(40021, "处理人无效或非在职工程师", 400),
    NO_AUTH(40100, "缺少 X-User-Id 请求头，请先模拟登录", 401),
    USER_INVALID(40101, "用户不存在或已禁用", 401),
    FORBIDDEN(40300, "权限不足", 403),
    TICKET_NOT_FOUND(40400, "工单不存在", 404),
    IDEMPOTENT_CONFLICT(40901, "重复提交", 409),
    ILLEGAL_TRANSITION(40910, "非法状态转移", 409),
    NOT_CLAIMABLE(40911, "当前工单不可领取，请使用派单功能", 409),
    ALREADY_CLAIMED(40912, "手慢了，该工单已被其他工程师领取", 409),
    SYSTEM_ERROR(50000, "服务器内部错误", 500);

    private final int code;
    private final String msg;
    private final int httpStatus;

    ErrorCode(int code, String msg, int httpStatus) {
        this.code = code;
        this.msg = msg;
        this.httpStatus = httpStatus;
    }
}
