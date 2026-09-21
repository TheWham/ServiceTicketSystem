package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 工单流转日志(it_ticket.ticket_flow_log) */
@Data
@TableName("ticket_flow_log")
public class TicketFlowLog {
    @TableId(value = "log_id", type = IdType.AUTO)
    private Long logId;
    private String ticketId;
    private String fromStatus;
    private String toStatus;
    private String operatorId;
    private String remark;
    private LocalDateTime createdAt;
}
