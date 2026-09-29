package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.EngineerPresence;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 工程师在线状态(SQL-010 engineer_runtime_state)。[LOCAL]
 * PRD 6.2:只有 AVAILABLE 可分配新咨询。
 * lastAssignedAt 用于 PRD 12.1 第 4 条"负载相同时选最久未收到新任务者"。
 */
@Data
@TableName("engineer_runtime_state")
public class EngineerRuntimeState {

    @TableId(value = "engineer_id", type = IdType.INPUT)
    private String engineerId;
    private EngineerPresence presence;
    private LocalDateTime lastActivityAt;
    private LocalDateTime lastAssignedAt;
    private Long version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
