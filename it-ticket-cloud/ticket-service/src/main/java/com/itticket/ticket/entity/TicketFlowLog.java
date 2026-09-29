package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.TableField;
import lombok.Data;

import java.time.LocalDateTime;

/** 工单流转日志（ticket_transition，只追加不覆盖 §2.2；PRD-Ultimate §20） */
@Data
@TableName("ticket_transition")
@com.fasterxml.jackson.databind.annotation.JsonNaming(com.fasterxml.jackson.databind.PropertyNamingStrategies.SnakeCaseStrategy.class)
public class TicketFlowLog {
    @TableId(value = "transition_id", type = IdType.ASSIGN_ID)
    private String transitionId;
    private String ticketId;
    private String fromStatus;
    private String toStatus;
    /** 流转事件（§9.3：SUBMIT/ROUTE/ACCEPT/SUPPLEMENT_REQUEST/...） */
    @TableField("event")
    private String event;
    private String operatorId;
    /** 驳回/撤销/异常关闭必填 */
    private String reason;
    private LocalDateTime occurredAt;
}
