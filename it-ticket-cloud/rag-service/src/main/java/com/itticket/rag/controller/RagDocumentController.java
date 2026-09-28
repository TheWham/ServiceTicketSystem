package com.itticket.rag.controller;

import com.itticket.common.api.Result;
import com.itticket.rag.dto.DocumentUploadRequest;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.service.ElasticsearchIndexService;
import com.itticket.rag.service.RagPipelineService;
import com.itticket.rag.vo.DocumentUploadResultVO;
import com.itticket.rag.vo.PipelineTraceVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

/**
 * ============================================================================
 * RAG 知识库与链路追踪 HTTP 控制器 (RagDocumentController)
 * ============================================================================
 *
 * 【接口列表】：
 * 1. POST /api/v1/rag/documents/upload : 上传文档并触发解析、切片、写入 ES 完整链路
 * 2. GET  /api/v1/rag/traces/{traceId}  : 查询指定 TraceId 的全链路明细与切片列表
 * 3. GET  /api/v1/rag/traces           : 获取最近执行的历史链路列表
 * 4. POST /api/v1/rag/indices/init     : 手动初始化或重建 Elasticsearch 知识切片索引
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/rag")
@RequiredArgsConstructor
public class RagDocumentController {

    private final RagPipelineService pipelineService;
    private final ElasticsearchIndexService indexService;

    /**
     * 手动初始化/新建 ES 知识切片索引
     *
     * @param recreate 是否强制删除后重建索引（默认 false）
     * @return 包含 ES 节点及初始化状态的响应报文
     */
    @PostMapping("/indices/init")
    public Result<Map<String, Object>> initIndex(
            @RequestParam(value = "recreate", required = false, defaultValue = "false") boolean recreate
    ) {
        log.info("Request to init ES index, recreate: {}", recreate);
        return Result.ok(indexService.createIndexExplicitly(recreate));
    }

    /**
     * 上传文档并执行切片、入库 ES 完整链路
     *
     * @param file         上传的 Markdown 或 TXT 文件流
     * @param title        自定义文档标题（可选，留空则自动从 Markdown 提取）
     * @param categoryId   知识分类编码（默认 C_NET）
     * @param riskLevel    知识风险等级（LOW, MEDIUM, HIGH）
     * @param chunkSize    目标切片字符数（默认 500）
     * @param chunkOverlap 切片重叠字符数（默认 50）
     * @param minChunkSize 最小切片字符数（默认 30）
     * @return DocumentUploadResultVO 包含持久化记录与全链路处理报告
     */
    @PostMapping(value = "/documents/upload", consumes = "multipart/form-data")
    public Result<DocumentUploadResultVO> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "title", required = false) String title,
            @RequestParam(value = "categoryId", required = false, defaultValue = "C_NET") String categoryId,
            @RequestParam(value = "riskLevel", required = false, defaultValue = "LOW") String riskLevel,
            @RequestParam(value = "chunkSize", required = false, defaultValue = "500") Integer chunkSize,
            @RequestParam(value = "chunkOverlap", required = false, defaultValue = "50") Integer chunkOverlap,
            @RequestParam(value = "minChunkSize", required = false, defaultValue = "30") Integer minChunkSize
    ) {
        DocumentUploadRequest request = new DocumentUploadRequest();
        request.setTitle(title);
        request.setCategoryId(categoryId);
        try {
            request.setRiskLevel(KnowledgeRiskLevel.valueOf(riskLevel.toUpperCase()));
        } catch (Exception e) {
            request.setRiskLevel(KnowledgeRiskLevel.LOW);
        }
        if (chunkSize != null) request.setChunkSize(chunkSize);
        if (chunkOverlap != null) request.setChunkOverlap(chunkOverlap);
        if (minChunkSize != null) request.setMinChunkSize(minChunkSize);

        log.info("Received document upload: {} (size: {} bytes, chunkSize: {}, overlap: {})",
                file.getOriginalFilename(), file.getSize(), request.getChunkSize(), request.getChunkOverlap());

        DocumentUploadResultVO result = pipelineService.processDocumentUpload(file, request);
        return Result.ok(result);
    }

    /**
     * 获取指定 TraceId 的链路详情
     *
     * @param traceId 链路追踪全局唯一 ID
     * @return PipelineTraceVO 链路阶段与切片列表
     */
    @GetMapping("/traces/{traceId}")
    public Result<PipelineTraceVO> getTrace(@PathVariable("traceId") String traceId) {
        return Result.ok(pipelineService.getTraceById(traceId));
    }

    /**
     * 获取最近执行的历史链路列表
     *
     * @return List<PipelineTraceVO> 历史链路报告简要列表
     */
    @GetMapping("/traces")
    public Result<List<PipelineTraceVO>> listTraces() {
        return Result.ok(pipelineService.listRecentTraces());
    }
}
