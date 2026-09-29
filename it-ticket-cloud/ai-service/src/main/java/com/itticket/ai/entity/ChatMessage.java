package com.itticket.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;

/** 会话消息(it_ai.ai_chat_message),员工/AI/客服/系统发言统一存储;对外 JSON 统一 snake_case */
@Data
@TableName("ai_chat_message")
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ChatMessage {
    /** 发送人类型 */
    public static final String SENDER_USER = "USER";
    public static final String SENDER_AI = "AI";
    public static final String SENDER_AGENT = "AGENT";
    public static final String SENDER_SYSTEM = "SYSTEM";

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    /** USER/AI/AGENT/SYSTEM */
    private String senderType;
    /** 发送人ID(AI/SYSTEM 为空) */
    private String senderId;
    private String content;
    private LocalDateTime createTime;
}
