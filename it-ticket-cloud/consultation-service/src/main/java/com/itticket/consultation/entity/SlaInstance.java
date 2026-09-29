package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.AssignmentBizType;
import com.itticket.consultation.enums.SlaStatus;
import com.itticket.consultation.enums.SlaType;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * SLA 投影(DM-004)。咨询响应 SLA 不存在合法暂停原因(SlaPauseReason 只覆盖工单等待),
 * 因此本服务不写 sla_pause,pausedSeconds 恒为 0。
 * 记录 calendarId/calendarVersion 以便日历变更后仍可重算(AX-002)。
 */
@Data
@TableName("sla_instance")
public class SlaInstance {

    @TableId(value = "sla_id", type = IdType.INPUT)
    private String slaId;
    private AssignmentBizType bizType;
    private String bizId;
    private String ticketId;
    private SlaType slaType;
    private SlaStatus status;
    private Long targetWorkSeconds;
    private Long elapsedWorkSeconds;
    private Long pausedSeconds;
    private LocalDateTime targetAt;
    @com.baomidou.mybatisplus.annotation.TableField("breach_at")
    @com.fasterxml.jackson.annotation.JsonProperty("breach_at")
    private LocalDateTime breachedAt;
    private LocalDateTime metAt;
    private String calendarId;
    private Long calendarVersion;
    private Long version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
