package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 审计记录(DM-004),只追加,任何角色不得删除(SM-ROLE-001)。 */
@Data
@TableName("audit_log")
public class AuditLog {

    @TableId(value = "audit_id", type = IdType.INPUT)
    private String auditId;
    private String actorId;
    private String action;
    private String objectType;
    private String objectId;
    @com.baomidou.mybatisplus.annotation.TableField("before_value")
    @com.fasterxml.jackson.annotation.JsonProperty("before_value")
    private String beforeJson;
    @com.baomidou.mybatisplus.annotation.TableField("after_value")
    @com.fasterxml.jackson.annotation.JsonProperty("after_value")
    private String afterJson;
    private String reason;
    private String requestId;
    private LocalDateTime occurredAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
