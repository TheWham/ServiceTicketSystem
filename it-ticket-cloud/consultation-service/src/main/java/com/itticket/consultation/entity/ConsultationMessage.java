package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.MessageSenderType;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 咨询消息(DM-004),只追加。撤回只写撤回元数据,不删除正文(DM-005)。
 * clientMessageId 与 sessionId 组成唯一键,保证客户端重发不产生重复消息(RD-002)。
 */
@Data
@TableName("consultation_message")
public class ConsultationMessage {

    @TableId(value = "message_id", type = IdType.INPUT)
    private String messageId;
    private String sessionId;
    private String senderId;
    private MessageSenderType senderType;
    private String clientMessageId;
    private String content;
    /** KnowledgeCitation 列表的 JSON,仅 AI 消息写入。 */
    private String citationJson;
    private LocalDateTime sentAt;
    private LocalDateTime withdrawnAt;
    private String withdrawReason;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
