package com.itticket.user.vo;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

/** 草稿响应(snake_case,attachment_urls 为数组,与旧版 JSON.parse 后一致) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class DraftVO {
    private Long draftId;
    private String userId;
    private String title;
    private String category;
    private String subCategory;
    private String priority;
    private String description;
    private List<String> attachmentUrls;
    private String assetId;
    private LocalDateTime expectedFinishTime;
    private LocalDateTime updatedAt;
}
