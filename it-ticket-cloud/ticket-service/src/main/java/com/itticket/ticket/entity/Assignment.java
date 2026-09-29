package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 分配记录（PRD §12.3：转派不删历史责任） */
@Data
@TableName("assignment")
public class Assignment {
    @TableId(value = "assignment_id", type = IdType.INPUT)
    private String assignmentId;
    /** CONSULTATION / TICKET */
    private String bizType;
    private String bizId;
    private String engineerId;
    private LocalDateTime assignedAt;
    /** 响应 SLA 截止（10 工作分钟） */
    private LocalDateTime responseDeadline;
    /** 首次有效响应 */
    private LocalDateTime respondedAt;
    /** RESPONDED / TIMEOUT_TRANSFER / TRANSFER_APPLY */
    private String endReason;
    private LocalDateTime createdAt;
}
