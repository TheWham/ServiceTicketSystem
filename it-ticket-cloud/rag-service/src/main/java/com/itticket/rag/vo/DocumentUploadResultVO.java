package com.itticket.rag.vo;

import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeVersion;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * ============================================================================
 * 文档上传结果 (DocumentUploadResultVO)
 * ============================================================================
 *
 * 【内容】：持久化的文章与版本实体 + 全链路追踪报告。
 * 文章初始状态取决于 publishNow：true ➔ PUBLISHED（快速通道）/
 * false ➔ DRAFT（标准生命周期，SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90）。
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DocumentUploadResultVO {
    private KnowledgeArticle article;
    private KnowledgeVersion version;
    private PipelineTraceVO trace;
}
