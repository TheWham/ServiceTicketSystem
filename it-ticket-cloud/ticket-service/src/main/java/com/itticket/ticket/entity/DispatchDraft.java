package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 派单草案（dispatch_draft）—— HITL 写操作门禁的承载实体。
 *
 * <p>需求依据：docs/IT服务工单系统-需求归因文档.md 功能 D
 * 「强制 Human-in-the-Loop 人机确认（派单草案主管点击才生效）；派单幂等防重与失败补偿」。
 *
 * <p>路由不再直接写 assignment，而是先落一份 PENDING 草案挂起；只有审批人
 * （PRD §98：系统不设主管角色，故为 PLATFORM_ADMIN）确认后才真正分派。
 * 同一工单同时只允许存在一份 PENDING 草案（DB 生成列唯一键 uk_dispatch_draft_pending）。
 */
@Data
@TableName("dispatch_draft")
public class DispatchDraft {

    public static final String STATUS_PENDING = "PENDING";
    public static final String STATUS_APPROVED = "APPROVED";
    public static final String STATUS_REJECTED = "REJECTED";
    public static final String STATUS_EXPIRED = "EXPIRED";

    @TableId(value = "draft_id", type = IdType.INPUT)
    private String draftId;
    private String ticketId;
    /** PENDING / APPROVED / REJECTED / EXPIRED */
    private String status;
    /** 草案建议的工程师 */
    private String engineerId;
    private String engineerName;
    private String teamId;
    private String priority;
    private String categoryId;
    /** 选人依据（负载/团队顺序等），供审批人判断 */
    private String selectionNote;
    /** 草案结构化载荷（对讲义 AuditDecisionPayload 的结构化契约） */
    private String payloadJson;
    /** 幂等键：同一工单同一轮路由只落一份草案 */
    private String idempotencyKey;
    @TableField(value = "version", update = "%s+1")
    private Long version;
    /** 草案失效时刻（对齐讲义「专属 Token 含超时失效」） */
    private LocalDateTime expiresAt;
    /** 认领人：审批人先认领再裁决，避免多人重复裁决 */
    private String claimedBy;
    private LocalDateTime claimedAt;
    /** 裁决人 */
    private String resolvedBy;
    private LocalDateTime resolvedAt;
    /** 驳回原因 / 失效说明（驳回必填） */
    private String reason;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}