package com.itticket.user.entity;

import com.baomidou.mybatisplus.annotation.IdType;
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
    private String userId;
    /** INCIDENT / REQUEST */
    private String nature;
    private String categoryId;
    private String title;
    private String description;
    private String impactDescription;
    private String urgencyDescription;
    private String location;
    private String contact;
    private String assetId;
    private LocalDateTime updatedAt;
}
