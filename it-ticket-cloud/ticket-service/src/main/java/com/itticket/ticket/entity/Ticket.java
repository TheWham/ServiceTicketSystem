package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.Version;
import com.itticket.ticket.enums.TicketStatus;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 工单主表 ticket —— PRD-Ultimate §20 字段严格对齐。
 * 状态 §9.2 九态；优先级 §11.4 接单时按「影响×紧急」矩阵动态确认；
 * 提单幂等 §10.4 idempotency_key；乐观锁 version。
 */
@Data
@TableName("ticket")
public class Ticket {
    @TableId(value = "ticket_id", type = IdType.INPUT)
    private String ticketId;
    /** 创建人 */
    private String creatorId;
    /** 工单性质 INCIDENT/SERVICE_REQUEST */
    @TableField("ticket_nature")
    private String nature;
    /** 末级分类 id（关联 category，§10.2） */
    private String categoryId;
    /** 分类快照（停用分类保留 §10.1） */
    private String categorySnapshot;
    /** 标题 1~100 字符 */
    private String title;
    /** 问题描述 10~5000 字符 */
    private String description;
    /** 影响情况（接单确认用） */
    private String impactDescription;
    /** 紧急说明 */
    private String urgencyDescription;
    /** 办公地点（选填） */
    private String location;
    /** 本次联系方式（不反写身份源） */
    private String contact;
    /** 资产编号（选填，硬件建议填） */
    private String assetId;
    /** 资产核对状态 PENDING/VERIFIED（CMDB 超时降级 §10.2） */
    private String assetCheckStatus;
    /** 状态 §9.2 九态 */
    private TicketStatus status;
    /** 优先级 HIGH/MEDIUM/LOW，新单默认 MEDIUM，接单按矩阵确认 §11.4 */
    private String priority;
    /** 影响范围（矩阵输入，接单时填）SINGLE/DEPARTMENT/CROSS_DEPT */
    private String impactScope;
    /** 紧急程度（矩阵输入，接单时填）LOW/MEDIUM/HIGH */
    private String urgencyLevel;
    /** 当前负责人 */
    private String assigneeId;
    /** 来源咨询会话（咨询转单 §10.2） */
    private String sourceSessionId;
    /** Immutable JSON snapshot of submitted category/context fields. */
    private String fieldSnapshotJson;
    /** 48h 自动验收标记 */
    private Integer autoAccepted;
    /** 重新打开次数 */
    private Integer reopenCount;
    /** 提单幂等键（§10.4） */
    private String idempotencyKey;
    /** 乐观锁 */
    @Version
    private Long version;
    private LocalDateTime completedAt;
    private LocalDateTime closedAt;
    /** 首次有效响应时间（响应 SLA §11.2） */
    private LocalDateTime firstResponseAt;
    /** 解决方案提交时间 */
    private LocalDateTime solvedAt;
    /** 验收评分 */
    private Integer ratingScore;
    /** 验收评价 */
    private String ratingComment;
    /** 验收时间 */
    private LocalDateTime ratedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
