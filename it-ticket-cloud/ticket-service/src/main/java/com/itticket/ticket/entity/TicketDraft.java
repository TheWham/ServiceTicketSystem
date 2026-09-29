package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.FieldStrategy;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/** 提单草稿(it_ticket.ticket_draft,spec 05 saveTicketDraft / SQL-010:每员工一个活动草稿) */
@Data
@TableName("ticket_draft")
public class TicketDraft {
    @TableId(value = "draft_id", type = IdType.INPUT)
    private String draftId;
    private String creatorId;
    /** 残缺字段也允许保存(PRD 10.4),payload 的 JSON 序列化 */
    private String payloadJson;
    @TableField(updateStrategy = FieldStrategy.ALWAYS)
    private String nature;
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

    private LocalDateTime lastSavedAt;
    private LocalDateTime expiresAt;
    private Long version;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
