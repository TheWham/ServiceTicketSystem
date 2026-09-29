package com.itticket.ticket.feign;

/** 咨询转工单通知:ticket-service 建单成功后回调 consultation-service 的内部接口(PRD 9.1、SM-CONSULT-001)。 */
public record ConvertedNotice(String ticketId) {
}
