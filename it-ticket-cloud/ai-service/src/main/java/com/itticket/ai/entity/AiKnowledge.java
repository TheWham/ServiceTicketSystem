package com.itticket.ai.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

import java.time.LocalDateTime;

/** AI 知识库切片(it_ai.ai_knowledge);对外 JSON 统一 snake_case */
@Data
@TableName("ai_knowledge")
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class AiKnowledge {
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;
    private String title;
    /** 切片文本 */
    private String content;
    /** TICKET=历史工单 DOC=外部文档 MANUAL=手工录入 */
    private String sourceType;
    /** 来源标识(工单号/文档名),防重复入库 */
    private String sourceId;
    private String category;
    /** 向量,JSON 数组字符串 */
    private String embedding;
    private LocalDateTime createTime;
}
