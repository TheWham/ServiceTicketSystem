package com.itticket.ai.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/** 手工录入知识请求(客服/主管维护 FAQ、SOP 等) */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class KnowledgeAddRequest {
    private String title;
    /** 知识正文(过长会自动切片) */
    private String content;
    private String category;
}
