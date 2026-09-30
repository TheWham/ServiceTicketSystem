package com.itticket.rag.dto;

import com.itticket.rag.enums.KnowledgeRiskLevel;
import lombok.Data;

/**
 * ============================================================================
 * 文档上传请求 (DocumentUploadRequest)
 * ============================================================================
 *
 * 【规范引用】（路径相对仓库根目录 docs/）：
 * - SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90
 *     publishNow=false 落 DRAFT 走标准生命周期；true 为兼容快速直发通道。
 * - AI-002 · specs/02-ai-api-json-schema.md:25
 *     authorId 由控制器从网关认证上下文注入，不信任请求体传入。
 * - DM-002 · specs/01-data-model-strong-types.md:41
 *     风险等级契约值域 NORMAL / HIGH（历史 LOW/MEDIUM 入库前归一）。
 */
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
     * （submit ➔ publish）才会切片并进入检索索引
     * （SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90；
     * AI-001 · specs/02-ai-api-json-schema.md:14：未发布内容不得进入索引）。</p>
     */
    private boolean publishNow = true;

    private int chunkSize = 500;
    private int chunkOverlap = 50;
    private int minChunkSize = 30;
}
