package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 异常队列(SQL-010 exception_queue / RD-005)。
 * 候选工程师耗尽等情形写入,由平台管理员处理。
 * (objectType, objectId, reasonCode, status) 唯一,保证同一原因不重复入队。
 */
@Data
@TableName("exception_queue")
public class ExceptionQueueItem {

    /** 一期本地状态值:SQL-010 未约束取值,故不放入 DM-002 枚举目录。 */
    public static final String STATUS_OPEN = "OPEN";

    public static final String OBJECT_TYPE_CONSULTATION = "CONSULTATION";
    public static final String REASON_CANDIDATES_EXHAUSTED = "CONSULTATION_CANDIDATES_EXHAUSTED";
    public static final String REASON_NO_ROUTE = "CONSULTATION_NO_ROUTE";

    @TableId(value = "exception_id", type = IdType.INPUT)
    private String exceptionId;
    private String objectType;
    private String objectId;
    private String reasonCode;
    private String status;
    private String claimedBy;
    private LocalDateTime claimedAt;
    private String resolvedBy;
    private LocalDateTime resolvedAt;
    private String reason;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
