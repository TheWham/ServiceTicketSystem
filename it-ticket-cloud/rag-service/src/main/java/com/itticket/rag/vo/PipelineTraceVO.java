package com.itticket.rag.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * ============================================================================
 * RAG 全链路追踪报告值对象 (PipelineTraceVO)
 * ============================================================================
 *
 * 【汇报与审计作用】：
 * 提供一次文档摄入（Ingestion）操作的端到端可观测性（Observability）报告，
 * 包含解析耗时、切片数量、Token 预估、ES 写入状态、以及各切片的正文明细。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PipelineTraceVO {
    /** 链路追踪全局唯一 ID (如 "trc-a1b2c3d4e5f6") */
    private String traceId;

    /** 文档主标题 */
    private String documentName;

    /** 原始文件格式后缀 (md, txt) */
    private String fileType;

    /** 原始文件大小 (字节) */
    private long fileSize;

    /** 关联生成的 MySQL 知识文章 ID */
    private String articleId;

    /** 关联生成的 MySQL 知识版本 ID */
    private String versionId;

    /** 所属知识分类编码 (C_NET, C_SW 等) */
    private String categoryId;

    /** 全链路最终状态 (SUCCESS-成功, FAILED-失败, RUNNING-处理中) */
    private String status;

    /** 链路处理开始时间 */
    private LocalDateTime startTime;

    /** 链路处理完成时间 */
    private LocalDateTime endTime;

    /** 全链路总耗时 (毫秒) */
    private long totalDurationMs;

    /** 执行摘要简述 */
    private String summary;

    /** 各子阶段执行报告列表 (PARSING, CHUNKING, ES_INDEXING) */
    @Builder.Default
    private List<PipelineStageVO> stages = new ArrayList<>();

    /** 最终生成的语义切片明细列表 */
    @Builder.Default
    private List<KnowledgeChunkVO> chunks = new ArrayList<>();
}
