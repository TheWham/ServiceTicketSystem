package com.itticket.ticket.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/** 创建工单请求(前端传 snake_case 字段,与旧版 body 一致) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class CreateTicketRequest {
    private String title;
    private String category;
    private String description;
    private String priority;
    private List<String> attachmentUrls;
    private LocalDateTime expectedFinishTime;
    private String clientToken;
    private String assetId;
}
