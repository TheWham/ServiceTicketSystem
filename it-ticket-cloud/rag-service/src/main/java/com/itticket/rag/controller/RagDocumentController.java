package com.itticket.rag.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.rag.dto.DocumentUploadRequest;
import com.itticket.rag.dto.RagRetrievalRequest;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.service.ElasticsearchIndexService;
import com.itticket.rag.service.RagPipelineService;
import com.itticket.rag.service.RagRetrievalService;
import com.itticket.rag.vo.DocumentUploadResultVO;
import com.itticket.rag.vo.PipelineTraceVO;
import com.itticket.rag.vo.RagRetrievalResponse;
import jakarta.validation.Valid;
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
 * 5. POST /api/v1/rag/retrievals       : RAG 检索（供 AI 客服服务对接的已发布知识 Top-K 切片）
 *
 * <p>注：大模型生成与对话状态由 AI 客服服务负责，本模块只提供检索与知识策略判定。</p>
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
    private final RagRetrievalService retrievalService;

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
            @RequestParam(value = "riskLevel", required = false, defaultValue = "NORMAL") String riskLevel,
            @RequestParam(value = "publishNow", required = false, defaultValue = "true") boolean publishNow,
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
            request.setRiskLevel(KnowledgeRiskLevel.NORMAL);
        }
        // publishNow=false 走标准生命周期：落 DRAFT 且不写 ES，需经 submit ➔ publish 才进入检索索引
        request.setPublishNow(publishNow);
        // 作者取网关透传的认证上下文，不接受请求体传入（AI-002）
        request.setAuthorId(UserContext.get().getUserId());
        if (chunkSize != null) request.setChunkSize(chunkSize);
        if (chunkOverlap != null) request.setChunkOverlap(chunkOverlap);
        if (minChunkSize != null) request.setMinChunkSize(minChunkSize);

        log.info("Received document upload: {} (size: {} bytes, chunkSize: {}, overlap: {}, publishNow: {}, author: {})",
                file.getOriginalFilename(), file.getSize(), request.getChunkSize(), request.getChunkOverlap(),
                publishNow, request.getAuthorId());

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

    /**
     * RAG 检索：返回已发布知识的 Top-K 切片与策略判定，供 AI 客服服务对接。
     *
     * <p>强制过滤 status=PUBLISHED（AI-001 / AC-27）；命中高风险主题或相似度不足时，
     * 通过 reliable=false 与 suggestedRefusalReason 告知对接方应当拒答。</p>
     *
     * @param request 检索请求（question 必填，categoryId / topK 可选）
     */
    @PostMapping("/retrievals")
    public Result<RagRetrievalResponse> retrieve(@Valid @RequestBody RagRetrievalRequest request) {
        UserContext.get();
        log.info("RAG retrieval request: categoryId={}, topK={}", request.getCategoryId(), request.getTopK());
        RagRetrievalService.RetrievalOutcome outcome = retrievalService.retrieve(
                request.getQuestion(), request.getCategoryId(), request.getTopK());
        return Result.ok(retrievalService.toResponse(outcome));
    }
}
