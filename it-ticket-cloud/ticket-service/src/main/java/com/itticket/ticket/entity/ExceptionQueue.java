package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 异常队列（PRD §4：无人响应/路由失败/长期挂起/通知失败/超限 → 平台管理员处理） */
@Data
@TableName("exception_queue")
public class ExceptionQueue {
    @TableId(value = "exception_id", type = IdType.INPUT)
    private String exceptionId;
    /** TICKET / CONSULTATION / NOTIFICATION */
    private String bizType;
    /** 关联业务 ID */
    private String bizId;
    /** NO_RESPONSE / ROUTE_FAILED / LONG_PENDING / NOTIFY_FAILED / LIMIT_EXCEEDED */
    private String exceptionType;
    private String title;
    private String detail;
    private String priority;
    /** OPEN / RESOLVED / DISMISSED */
    private String status;
    private String resolvedBy;
    private LocalDateTime resolvedAt;
    private String resolution;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
