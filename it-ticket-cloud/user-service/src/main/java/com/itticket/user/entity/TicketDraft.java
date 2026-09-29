package com.itticket.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.FieldStrategy;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 提单草稿表(ticket_draft),每用户一条 —— 字段对齐新提单 §10.2 */
@Data
@TableName("ticket_draft")
public class TicketDraft {
    @TableId(value = "draft_id", type = IdType.ASSIGN_ID)
    private String draftId;
    @TableField("creator_id")
    private String userId;
    /** INCIDENT / REQUEST */
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String ticketNature;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String categoryId;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String title;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String description;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String impactDescription;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String urgencyDescription;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String location;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String contact;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String assetId;
    private String payloadJson;
    private Long version;
    private LocalDateTime createdAt;
    private LocalDateTime lastSavedAt;
    private LocalDateTime expiresAt;
    private LocalDateTime updatedAt;
}
