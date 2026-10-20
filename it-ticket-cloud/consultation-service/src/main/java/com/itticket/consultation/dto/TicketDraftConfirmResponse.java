package com.itticket.consultation.dto;

/**
 * 员工确认建单结果(人机回环第二步)。
 *
 * @param ticketId 新建的工单号(由 ticket-service 生成)
 */
public record TicketDraftConfirmResponse(String ticketId) {
}