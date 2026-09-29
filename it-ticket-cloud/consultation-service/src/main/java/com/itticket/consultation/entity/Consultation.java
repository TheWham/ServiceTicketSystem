package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.ConsultationResolutionType;
import com.itticket.consultation.enums.ConsultationSource;
import com.itticket.consultation.enums.ConsultationStatus;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 咨询会话(DM-004)。状态字段的合法变化只允许经 SM-CONSULT-001 的迁移表发生。
 * version 是乐观锁,所有更新必须带 version 条件(DM-001)。时间列为 UTC 挂钟时间。
 */
@Data
@TableName("consultation")
public class Consultation {

    @TableId(value = "session_id", type = IdType.INPUT)
    private String sessionId;
    private String creatorId;
    private String categoryId;
    private ConsultationStatus status;
    private String currentEngineerId;
    private ConsultationSource source;
    private ConsultationResolutionType resolutionType;
    private String convertedTicketId;
    private LocalDateTime closedAt;
    private Long version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
