package com.itticket.rag.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.rag.dto.DifyRetrievalRequest;
import com.itticket.rag.dto.DifyTextDocumentRequest;
import com.itticket.rag.service.DifyKnowledgeService;
import com.itticket.rag.vo.DifyDocumentUploadResultVO;
import com.itticket.rag.vo.DifyRetrievalResultVO;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * ============================================================================
 * Dify 知识库通道 HTTP 控制器 (DifyKnowledgeController)
 * ============================================================================
 *
 * 【接口列表】（与自研 ES 链路并行，互不影响）：
 * 1. POST /api/v1/rag/dify/datasets            : 初始化/复用 Dify 知识库
 * 2. POST /api/v1/rag/dify/documents/upload    : 上传文档（Dify 完成解析/分块/向量化/混合索引）
 * 3. POST /api/v1/rag/dify/documents/text      : 按纯文本创建文档
 * 4. GET  /api/v1/rag/dify/documents/{batch}/status : 查询批次索引状态
 * 5. POST /api/v1/rag/dify/retrievals          : 混合召回（默认 hybrid_search）
 *
 * <p>密钥由环境变量 DIFY_API_KEY 注入；操作者身份取网关透传上下文（AI-002）。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/rag/dify")
@RequiredArgsConstructor
public class DifyKnowledgeController {

    private final DifyKnowledgeService difyKnowledgeService;

    /** 初始化/复用 Dify 知识库，返回 datasetId */
    @PostMapping("/datasets")
    public Result<Map<String, Object>> ensureDataset() {
        String operator = UserContext.get().getUserId();
        var dataset = difyKnowledgeService.ensureDataset();
        log.info("Dify 知识库就绪: id={}, name={}, operator={}", dataset.getId(), dataset.getName(), operator);
        return Result.ok(Map.of(
                "datasetId", dataset.getId() == null ? "" : dataset.getId(),
                "name", dataset.getName() == null ? "" : dataset.getName(),
                "indexingTechnique", dataset.getIndexingTechnique() == null ? "" : dataset.getIndexingTechnique(),
                "documentCount", dataset.getDocumentCount() == null ? 0 : dataset.getDocumentCount()
        ));
    }

    /**
     * 上传文档到 Dify 知识库（解析/分块/向量化/混合索引由 Dify 完成）。
     *
     * @param file         文档文件（txt/md/pdf/docx 等）
     * @param chunkSize    自定义切片 token 数；&lt;=0 使用 Dify 自动分段
     * @param chunkOverlap 切片重叠 token 数（默认 50）
     * @param waitSeconds  请求内等待索引完成的最长秒数（默认 60；0 立即返回）
     */
    @PostMapping(value = "/documents/upload", consumes = "multipart/form-data")
    public Result<DifyDocumentUploadResultVO> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "chunkSize", required = false, defaultValue = "0") Integer chunkSize,
            @RequestParam(value = "chunkOverlap", required = false, defaultValue = "50") Integer chunkOverlap,
            @RequestParam(value = "waitSeconds", required = false) Integer waitSeconds
    ) {
        String operator = UserContext.get().getUserId();
        log.info("Dify 文档上传请求: file={}, operator={}", file.getOriginalFilename(), operator);
        return Result.ok(difyKnowledgeService.uploadDocument(
                file, chunkSize == null ? 0 : chunkSize, chunkOverlap == null ? 50 : chunkOverlap, waitSeconds));
    }

    /** 按纯文本创建 Dify 文档 */
    @PostMapping("/documents/text")
    public Result<DifyDocumentUploadResultVO> createDocumentByText(
            @Valid @RequestBody DifyTextDocumentRequest request
    ) {
        String operator = UserContext.get().getUserId();
        log.info("Dify 文本文档创建请求: name={}, operator={}", request.getName(), operator);
        return Result.ok(difyKnowledgeService.createDocumentByText(
                request.getName(), request.getText(),
                request.getChunkSize() == null ? 0 : request.getChunkSize(),
                request.getChunkOverlap() == null ? 50 : request.getChunkOverlap(),
                request.getWaitSeconds()));
    }

    /** 查询批次索引状态（waiting ➔ parsing ➔ cleaning ➔ splitting ➔ indexing ➔ completed/error） */
    @GetMapping("/documents/{batch}/status")
    public Result<List<DifyDocumentUploadResultVO.Item>> getIndexingStatus(@PathVariable("batch") String batch) {
        return Result.ok(difyKnowledgeService.getIndexingStatus(batch));
    }

    /** Dify 混合召回（默认 hybrid_search：向量+关键词双路召回） */
    @PostMapping("/retrievals")
    public Result<DifyRetrievalResultVO> retrieve(@Valid @RequestBody DifyRetrievalRequest request) {
        UserContext.get();
        log.info("Dify 召回请求: method={}, topK={}", request.getSearchMethod(), request.getTopK());
        return Result.ok(difyKnowledgeService.retrieve(request));
    }
}
