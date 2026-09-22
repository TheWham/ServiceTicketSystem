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
    private String category;
    private String subCategory;
    private String priority;
    private TicketStatus status;
    private String creatorId;
    private String assigneeId;
    private String assetId;
    private LocalDateTime expectedFinishTime;
    /** JSON 数组字符串,如 ["url1","url2"] */
    private String attachmentUrls;
    /** 幂等防重 token */
    private String clientToken;
    private LocalDateTime firstResponseAt;
    private LocalDateTime solvedAt;
    private Integer pauseMinutes;
    private Integer ratingScore;
    private String ratingComment;
    private LocalDateTime ratedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
