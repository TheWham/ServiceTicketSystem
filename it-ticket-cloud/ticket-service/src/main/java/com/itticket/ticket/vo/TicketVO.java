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
 * 工单响应(snake_case + creator_name/assignee_name,与旧版 SELECT t.* JOIN user 的行结构一致)
 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
@JsonIgnoreProperties(ignoreUnknown = true)
public class TicketVO {
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
    private List<String> attachmentUrls;
    private String clientToken;
    private LocalDateTime firstResponseAt;
    private LocalDateTime solvedAt;
    private Integer pauseMinutes;
    private Integer ratingScore;
    private String ratingComment;
    private LocalDateTime ratedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String creatorName;
    private String assigneeName;

    public static TicketVO from(Ticket t) {
        TicketVO vo = new TicketVO();
        vo.setTicketId(t.getTicketId());
        vo.setTitle(t.getTitle());
        vo.setDescription(t.getDescription());
        vo.setCategory(t.getCategory());
        vo.setSubCategory(t.getSubCategory());
        vo.setPriority(t.getPriority());
        vo.setStatus(t.getStatus());
        vo.setCreatorId(t.getCreatorId());
        vo.setAssigneeId(t.getAssigneeId());
        vo.setAssetId(t.getAssetId());
        vo.setExpectedFinishTime(t.getExpectedFinishTime());
        vo.setClientToken(t.getClientToken());
        vo.setFirstResponseAt(t.getFirstResponseAt());
        vo.setSolvedAt(t.getSolvedAt());
        vo.setPauseMinutes(t.getPauseMinutes());
        vo.setRatingScore(t.getRatingScore());
        vo.setRatingComment(t.getRatingComment());
        vo.setRatedAt(t.getRatedAt());
        vo.setCreatedAt(t.getCreatedAt());
        vo.setUpdatedAt(t.getUpdatedAt());
        return vo;
    }
}
