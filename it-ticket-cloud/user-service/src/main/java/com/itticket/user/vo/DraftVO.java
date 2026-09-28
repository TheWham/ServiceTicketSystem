package com.itticket.user.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;

/** 草稿响应(snake_case，对齐新提单字段 §10.2) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class DraftVO {
    private Long draftId;
    private String userId;
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
