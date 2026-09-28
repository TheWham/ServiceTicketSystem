package com.itticket.rag.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * ============================================================================
 * RAG 单个执行阶段报告值对象 (PipelineStageVO)
 * ============================================================================
 *
 * 【阶段划分】：
 * - PARSING     : 文档读取、格式校验、标题识别
 * - CHUNKING    : 语义切分、重叠滑动、Token 估算
 * - ES_INDEXING : ES 索引探测、Schema Mapping、批量写入
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PipelineStageVO {
    /** 阶段代号 (PARSING, CHUNKING, ES_INDEXING, ERROR) */
    private String stageCode;

    /** 阶段人类可读名称 (如 "文档解析与文本提取") */
    private String stageName;

    /** 阶段业务行为描述 */
    private String description;

    /** 阶段执行状态 (SUCCESS, WARNING, FAILED, SKIPPED) */
    private String status;

    /** 阶段独立耗时 (毫秒) */
    private long durationMs;

    /** 阶段启动时间 */
    private LocalDateTime startTime;

    /** 阶段结束时间 */
    private LocalDateTime endTime;

    /** 阶段执行反馈消息 */
    private String message;

    /** 阶段关键度量指标字典 (如字符数、行数、Token数、ES节点等) */
    private Map<String, Object> metrics;
}
