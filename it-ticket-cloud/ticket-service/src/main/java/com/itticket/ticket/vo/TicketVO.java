package com.itticket.ticket.vo;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.enums.TicketStatus;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 工单响应 VO —— PRD-Ultimate §20 字段对齐（snake_case 输出）。
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
@JsonIgnoreProperties(ignoreUnknown = true)
public class TicketVO {
    private String ticketId;
    private String creatorId;
    private String nature;
    private String categoryId;
    private String categorySnapshot;
    private String title;
    private String description;
    private String impactDescription;
    private String urgencyDescription;
    private String location;
    private String contact;
    private String assetId;
    private String assetCheckStatus;
    private TicketStatus status;
    private String priority;
    private String impactScope;
    private String urgencyLevel;
    private String assigneeId;
    private String sourceSessionId;
    private String fieldDefinitionSnapshot;
    private Integer autoAccepted;
    private Integer reopenCount;
    private LocalDateTime firstResponseAt;
    private LocalDateTime solvedAt;
    private LocalDateTime completedAt;
    private LocalDateTime closedAt;
    private Integer ratingScore;
    private String ratingComment;
    private LocalDateTime ratedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    /** 附件 URL 列表（来自 attachment 表） */
    private List<String> attachments;
    private String creatorName;
    private String assigneeName;

    public static TicketVO from(Ticket t) {
        TicketVO vo = new TicketVO();
        vo.setTicketId(t.getTicketId());
        vo.setCreatorId(t.getCreatorId());
        vo.setNature(t.getNature());
        vo.setCategoryId(t.getCategoryId());
        vo.setCategorySnapshot(t.getCategorySnapshot());
        vo.setTitle(t.getTitle());
        vo.setDescription(t.getDescription());
        vo.setImpactDescription(t.getImpactDescription());
        vo.setUrgencyDescription(t.getUrgencyDescription());
        vo.setLocation(t.getLocation());
        vo.setContact(t.getContact());
        vo.setAssetId(t.getAssetId());
        vo.setAssetCheckStatus(t.getAssetCheckStatus());
        vo.setStatus(t.getStatus());
        vo.setPriority(t.getPriority());
        vo.setImpactScope(t.getImpactScope());
        vo.setUrgencyLevel(t.getUrgencyLevel());
        vo.setAssigneeId(t.getAssigneeId());
        vo.setSourceSessionId(t.getSourceSessionId());
        vo.setFieldDefinitionSnapshot(t.getFieldDefinitionSnapshot());
        vo.setAutoAccepted(t.getAutoAccepted());
        vo.setReopenCount(t.getReopenCount());
        vo.setFirstResponseAt(t.getFirstResponseAt());
        vo.setSolvedAt(t.getSolvedAt());
        vo.setCompletedAt(t.getCompletedAt());
        vo.setClosedAt(t.getClosedAt());
        vo.setRatingScore(t.getRatingScore());
        vo.setRatingComment(t.getRatingComment());
        vo.setRatedAt(t.getRatedAt());
        vo.setCreatedAt(t.getCreatedAt());
        vo.setUpdatedAt(t.getUpdatedAt());
        return vo;
    }
}
