package com.itticket.rag.dto;

import lombok.Data;

@Data
public class ChunkConfigDTO {
    /** 每个切片的目标字符长度 (默认 500) */
    private int chunkSize = 500;

    /** 切片之间的重叠字符长度 (默认 50) */
    private int chunkOverlap = 50;

    /** 最小切片长度 (低于此长度合并到上一片或忽略, 默认 30) */
    private int minChunkSize = 30;
}
