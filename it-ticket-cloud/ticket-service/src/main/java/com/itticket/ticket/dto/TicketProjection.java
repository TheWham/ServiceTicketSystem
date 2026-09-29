package com.itticket.ticket.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;

import com.itticket.ticket.entity.Ticket;

/**
 * spec 05 TicketProjection(建单响应 data)。
 * priority 为 HIGH/MEDIUM/LOW;legacy 中文枚举值在此映射。
 */
@JsonPropertyOrder({"ticket_id", "status", "priority", "assignee_id", "version"})
public record TicketProjection(
        @JsonProperty("ticket_id") String ticketId,
        String status,
        String priority,
        @JsonProperty("assignee_id") String assigneeId,
        long version) {

    public static TicketProjection of(Ticket ticket) {
        return new TicketProjection(
                ticket.getTicketId(),
                ticket.getStatus().getValue(),
                toContractPriority(ticket.getPriority()),
                ticket.getAssigneeId(),
                ticket.getVersion() == null ? 0L : ticket.getVersion());
    }

    private static String toContractPriority(String legacy) {
        return switch (legacy == null ? "" : legacy) {
            case "高" -> "HIGH";
            case "低" -> "LOW";
            default -> "MEDIUM";
        };
    }
}
