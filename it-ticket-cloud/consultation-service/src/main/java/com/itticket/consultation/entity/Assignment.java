package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.AssignmentBizType;
import com.itticket.consultation.enums.AssignmentEndReason;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 人工分配任务(DM-004)。endReason 为 NULL 表示仍在进行中。
 * 同一咨询的历史分配全部保留,用于 RD-005 的每名候选人最多尝试一次判定。
 */
@Data
@TableName("assignment")
public class Assignment {

    @TableId(value = "assignment_id", type = IdType.INPUT)
    private String assignmentId;
    private AssignmentBizType bizType;
    private String bizId;
    private String engineerId;
    private LocalDateTime assignedAt;
    private LocalDateTime responseDeadline;
    private LocalDateTime respondedAt;
    private AssignmentEndReason endReason;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
