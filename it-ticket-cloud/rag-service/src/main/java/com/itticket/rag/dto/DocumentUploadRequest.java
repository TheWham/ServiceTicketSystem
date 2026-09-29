package com.itticket.rag.dto;

import com.itticket.rag.enums.KnowledgeRiskLevel;
import lombok.Data;

@Data
public class DocumentUploadRequest {
    private String title;
    private String categoryId;

    /** 风险等级，契约值域 NORMAL / HIGH（历史 LOW / MEDIUM 会在入库前归一为 NORMAL） */
    private KnowledgeRiskLevel riskLevel = KnowledgeRiskLevel.NORMAL;

    private String authorId;

    /**
     * 是否上传后立即发布（兼容既有一站式快速通道，默认 true）。
     *
     * <p>false 时文章落 DRAFT 且不写入 ES，需走标准生命周期
     * （submit ➔ publish）才会切片并进入检索索引，见 SM-KNOWLEDGE-001。</p>
     */
    private boolean publishNow = true;

    private int chunkSize = 500;
    private int chunkOverlap = 50;
    private int minChunkSize = 30;
}
