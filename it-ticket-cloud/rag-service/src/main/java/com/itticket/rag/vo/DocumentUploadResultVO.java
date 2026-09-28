package com.itticket.rag.vo;

import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeVersion;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentUploadResultVO {
    private KnowledgeArticle article;
    private KnowledgeVersion version;
    private PipelineTraceVO trace;
}
