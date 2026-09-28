package com.itticket.ai.dto;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/** 客服转工单请求;标题/描述留空时自动用会话摘要与对话记录生成 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ToTicketRequest {
    private String title;
    /** 问题分类(必填):硬件/软件/网络/账号/其他 */
    private String category;
    private String priority;
    private String description;
}
