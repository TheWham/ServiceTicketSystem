package com.itticket.rag.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * ============================================================================
 * AI 回答审计实体 (AiInteraction) - 对应数据库表 `ai_interaction`
 * ============================================================================
 *
 * 【契约规范说明 (AI-003 / PRD §17.2)】：
 * 1. 只保存回答审计、引用来源、知识版本、置信度、响应耗时与员工反馈；不作为训练语料自动发布。
 * 2. 原始对话正文、提示词与模型内部推理不进入本表。
 *
 * 【与 spec 06 目标 DDL 的差异（以线上实际表结构为准）】：
 * 实际列为 retrieved_versions / answer / confidence(decimal(4,3)) / refused / feedback / latency / created_at，
 * 而非 spec 的 retrieved_versions_json / latency_ms / occurred_at / updated_at。此处按线上表映射。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@TableName("ai_interaction")
public class AiInteraction {

    /** 交互记录业务 ID（长度上限 32） */
    @TableId(value = "interaction_id", type = IdType.INPUT)
    private String interactionId;

    /** 关联咨询会话 ID（长度上限 32） */
    private String sessionId;

    /** 实际调用的模型标识 */
    private String modelVersion;

    /** 引用知识版本 JSON（article_id / version_id / score 精简形式，长度上限 500） */
    private String retrievedVersions;

    /** 回答正文（拒答时为空） */
    private String answer;

    /** 置信度，范围 [0,1] */
    private BigDecimal confidence;

    /** 是否拒答 */
    private Boolean refused;

    /** 员工反馈：HELPFUL / NOT_HELPFUL / INCORRECT */
    private String feedback;

    /** 回答延迟（毫秒） */
    private Integer latency;

    /** 记录时间 */
    private LocalDateTime createdAt;
}
