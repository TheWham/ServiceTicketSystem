package com.itticket.consultation.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.consultation.enums.AiFeedbackType;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * AI 回答审计元数据(DM-004 / PRD 17.2)。
 * 只保存模型版本、检索到的知识版本、置信度、耗时与员工反馈;
 * 不保存提示词、模型推理过程或向量内容(AI-008)。
 */
@Data
@TableName("ai_interaction")
public class AiInteraction {

    @TableId(value = "interaction_id", type = IdType.INPUT)
    private String interactionId;
    private String sessionId;
    private String modelVersion;
    /** 命中的 knowledge_version.version_id 列表 JSON,索引版本可追溯(DM-004)。 */
    private String retrievedVersionsJson;
    private BigDecimal confidence;
    private AiFeedbackType feedback;
    private Long latencyMs;
    private LocalDateTime occurredAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
