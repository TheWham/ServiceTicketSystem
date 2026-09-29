package com.itticket.user.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/** 草稿保存请求(前端传 snake_case 字段，对齐新提单字段 §10.2) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class DraftRequest {
    @com.fasterxml.jackson.annotation.JsonAlias("nature")
    private String ticketNature;
    private String categoryId;
    private String title;
    private String description;
    private String impactDescription;
    private String urgencyDescription;
    private String location;
    private String contact;
    private String assetId;
}
