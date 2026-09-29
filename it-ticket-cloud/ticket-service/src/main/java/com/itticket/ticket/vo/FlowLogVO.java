package com.itticket.ticket.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.itticket.ticket.entity.TicketFlowLog;
import lombok.Data;

import java.time.LocalDateTime;

/** 流转日志响应（ticket_transition 行结构，PRD-Ultimate §20） */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class FlowLogVO {
    private String transitionId;
    private String ticketId;
    private String fromStatus;
    private String toStatus;
    private String event;
    private String operatorId;
    private String reason;
    private LocalDateTime occurredAt;
    private String operatorName;

    public static FlowLogVO from(TicketFlowLog f) {
        FlowLogVO vo = new FlowLogVO();
        vo.setTransitionId(f.getTransitionId());
        vo.setTicketId(f.getTicketId());
        vo.setFromStatus(f.getFromStatus());
        vo.setToStatus(f.getToStatus());
        vo.setEvent(f.getEvent());
        vo.setOperatorId(f.getOperatorId());
        vo.setReason(f.getReason());
        vo.setOccurredAt(f.getOccurredAt());
        return vo;
    }
}
