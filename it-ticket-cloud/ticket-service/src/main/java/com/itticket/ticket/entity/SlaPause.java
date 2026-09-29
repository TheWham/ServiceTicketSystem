package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** SLA 暂停（PRD §11.3：补充/外部等待期间暂停） */
@Data
@TableName("sla_pause")
public class SlaPause {
    @TableId(value = "pause_id", type = IdType.INPUT)
    private String pauseId;
    private String slaId;
    /** SUPPLEMENT / EXTERNAL */
    private String reasonType;
    private LocalDateTime startedAt;
    private LocalDateTime endedAt;
    private String operatorId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
