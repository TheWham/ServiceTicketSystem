package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** SLA 实例（PRD §11.2：完成 SLA 创建起算，验收阶段不消耗；breach_at 不可删除） */
@Data
@TableName("sla_instance")
public class SlaInstance {
    @TableId(value = "sla_id", type = IdType.INPUT)
    private String slaId;
    private String ticketId;
    /** RESPONSE / COMPLETION */
    private String slaType;
    private String prioritySnapshot;
    /** 目标时刻（按优先级工作时长推算，PRD §20 target_at） */
    private LocalDateTime targetAt;
    /** 累计有效工作秒 */
    private Long elapsedWorkSeconds;
    private Long pausedSeconds;
    /** 80% 提醒标记 */
    private Integer nearBreachNotified;
    /** 违约时间（不可删除 §11.2） */
    private LocalDateTime breachAt;
    /** RUNNING / PAUSED / STOPPED / BREACHED */
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
