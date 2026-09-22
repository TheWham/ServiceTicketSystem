package com.itticket.ticket.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.itticket.ticket.entity.TicketFlowLog;
import lombok.Data;

import java.time.LocalDateTime;

/** 流转日志响应(含 operator_name,与旧版 JOIN user 的行结构一致) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class FlowLogVO {
    private Long logId;
    private String ticketId;
    private String fromStatus;
    private String toStatus;
    private String operatorId;
    private String remark;
    private LocalDateTime createdAt;
    private String operatorName;

    public static FlowLogVO from(TicketFlowLog f) {
        FlowLogVO vo = new FlowLogVO();
        vo.setLogId(f.getLogId());
        vo.setTicketId(f.getTicketId());
        vo.setFromStatus(f.getFromStatus());
        vo.setToStatus(f.getToStatus());
        vo.setOperatorId(f.getOperatorId());
        vo.setRemark(f.getRemark());
        vo.setCreatedAt(f.getCreatedAt());
        return vo;
    }
}
