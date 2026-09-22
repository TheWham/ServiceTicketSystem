package com.itticket.user.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/** 草稿保存请求(前端传 snake_case 字段) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class DraftRequest {
    private String title;
    private String category;
    private String subCategory;
    private String priority;
    private String description;
    private List<String> attachmentUrls;
    private String assetId;
    private LocalDateTime expectedFinishTime;
}
