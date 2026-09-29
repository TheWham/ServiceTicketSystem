package com.itticket.consultation.dto;

/**
 * 员工排队状态。只有服务端已经绑定工程师时才返回 assigned=true;
 * waitingCount 包含当前员工自己的 WAITING_ENGINEER 会话。
 */
public record QueueStatusResponse(boolean assigned, int waitingCount) {
}
