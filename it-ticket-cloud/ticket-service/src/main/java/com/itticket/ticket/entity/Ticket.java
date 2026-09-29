package com.itticket.ticket.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.ticket.enums.TicketStatus;
import lombok.Data;

import java.time.LocalDateTime;

/** 工单核心表(it_ticket.ticket) */
@Data
@TableName("ticket")
public class Ticket {
    @TableId(value = "ticket_id", type = IdType.INPUT)
    private String ticketId;
    private String title;
    private String description;
    /** 分类名称展示投影(来源 ticket_category.name),legacy 列 */
    private String category;
    private String subCategory;
    private String priority;
    private TicketStatus status;
    /** 工单性质 INCIDENT/SERVICE_REQUEST(PRD 10.2,新契约必填) */
    private String ticketNature;
    /** 末级分类编号(PRD 10.2,必须为启用的末级分类) */
    private String categoryId;
    /** 影响情况 1-2000 字符 */
    private String impactDescription;
    /** 紧急说明 1-2000 字符 */
    private String urgencyDescription;
    /** 办公地点,选填 */
    private String location;
    /** 本次联系方式,默认来自身份源 */
    private String contact;
    private String creatorId;
    private String assigneeId;
    private String assetId;
    private LocalDateTime expectedFinishTime;
    /** JSON 数组字符串,如 ["url1","url2"] */
    private String attachmentUrls;
    /** 幂等防重 token */
    private String clientToken;
    /** 来源咨询会话(CS 前缀;咨询转单时由系统写入,PRD 10.2) */
    private String sourceSessionId;
    /** 分类扩展字段值快照(field_values 的 JSON 序列化) */
    private String fieldSnapshotJson;
    /** 乐观锁版本 */
    private Long version;
    private LocalDateTime firstResponseAt;
    private LocalDateTime solvedAt;
    private Integer pauseMinutes;
    private Integer ratingScore;
    private String ratingComment;
    private LocalDateTime ratedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
