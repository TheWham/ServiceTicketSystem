package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.IdempotencyStatus;
import lombok.Data;

import java.time.LocalDateTime;

/** 幂等记录(DM-004 / RD-002)。(ownerId, operation, idempotencyKey) 唯一。 */
@Data
@TableName("idempotency_record")
public class IdempotencyRecord {

    @TableId(value = "record_id", type = IdType.INPUT)
    private String recordId;
    private String ownerId;
    private String operation;
    private String idempotencyKey;
    private String requestHash;
    private IdempotencyStatus status;
    private String resultJson;
    private LocalDateTime expiresAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
