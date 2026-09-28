package com.itticket.rag.dto;

import com.itticket.rag.enums.KnowledgeRiskLevel;
import lombok.Data;

@Data
public class DocumentUploadRequest {
    private String title;
    private String categoryId;
    private KnowledgeRiskLevel riskLevel = KnowledgeRiskLevel.LOW;
    private String authorId;
    private int chunkSize = 500;
    private int chunkOverlap = 50;
    private int minChunkSize = 30;
}
