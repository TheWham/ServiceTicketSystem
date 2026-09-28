package com.itticket.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.itticket.ai.enums.SessionStatus;
import lombok.Data;

import java.time.LocalDateTime;

/** 咨询会话(it_ai.ai_chat_session);对外 JSON 统一 snake_case(与项目接口约定一致) */
@Data
@TableName("ai_chat_session")
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ChatSession {
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    /** 发起员工 */
    private String userId;
    private SessionStatus status;
    /** 接入的客服ID */
    private String agentId;
    /** 问题摘要(转人工时生成,供客服快速了解) */
    private String summary;
    private String rejectReason;
    /** 转工单后的工单号 */
    private String ticketId;
    /** 1=员工确认已解决 */
    private Integer resolved;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
