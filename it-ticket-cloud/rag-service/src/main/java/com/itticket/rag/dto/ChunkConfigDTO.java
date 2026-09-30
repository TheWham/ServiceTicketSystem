package com.itticket.rag.dto;

import lombok.Data;

/**
 * ============================================================================
 * 切片配置 (ChunkConfigDTO)
 * ============================================================================
 *
 * 【用途】：文档上传与知识发布（reindex）通道共用的切片参数。
 * 切片质量直接决定检索召回（MR-004 · specs/10-model-rag-integration.md:70 的检索链路输入）。
 */
@Data
public class ChunkConfigDTO {
    /** 每个切片的目标字符长度 (默认 500) */
    private int chunkSize = 500;

    /** 切片之间的重叠字符长度 (默认 50) */
    private int chunkOverlap = 50;

    /** 最小切片长度 (低于此长度合并到上一片或忽略, 默认 30) */
    private int minChunkSize = 30;
}
