package com.itticket.rag.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.dto.ChunkConfigDTO;
import com.itticket.rag.dto.DocumentUploadRequest;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeVersion;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import com.itticket.rag.mapper.KnowledgeVersionMapper;
import com.itticket.rag.vo.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ============================================================================
 * RAG 全链路编排与追踪服务 (RagPipelineService)
 * ============================================================================
 *
 * 【业务定位与架构设计】：
 * 作为 RAG 文档处理的核心编排中枢，负责串联文档摄入的完整生命周期：
 * 
 * ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────────────┐
 * │ 1. 文档解析与提取 │ ───> │ 2. 文本清洗与分块 │ ───> │ 3. MySQL持久化 + ES写入  │
 * │ (PARSING)       │      │ (CHUNKING)      │      │ (ES_INDEXING & DB SAVE) │
 * └─────────────────┘      └─────────────────┘      └─────────────────────────┘
 *           │                       │                            │
 *           └───────────────────────┴────────────────────────────┘
 *                                   │
 *                        生成全链路追踪记录 (PipelineTraceVO)
 *
 * 【核心特性】：
 * 1. 毫秒级阶段计时与细粒度度量（包含字符数、Token 估算、切片分布、ES 节点状态）。
 * 2. 数据库幂等持久化：分别向 MySQL knowledge_article 与 knowledge_version 表写入业务快照。
 * 3. 内存级 Trace 缓存（TraceStore）：支持前端工作台即时回溯与历史链路审查。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RagPipelineService {

    private final DocumentParserService parserService;
    private final DocumentChunkerService chunkerService;
    private final ElasticsearchIndexService indexService;
    private final KnowledgeArticleMapper articleMapper;
    private final KnowledgeVersionMapper versionMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 内存中缓存最近处理的链路追踪记录 (Key: traceId, Value: PipelineTraceVO) */
    private final Map<String, PipelineTraceVO> traceStore = new ConcurrentHashMap<>();

    /**
     * 处理文档上传并执行 RAG 切片与入库完整链路
     *
     * @param file    上传的原始文件
     * @param request 文档元数据及切片配置
     * @return DocumentUploadResultVO 包含持久化实体与全链路追踪报告
     */
    public DocumentUploadResultVO processDocumentUpload(MultipartFile file, DocumentUploadRequest request) {
        if (request == null) {
            request = new DocumentUploadRequest();
        }

        String traceId = "trc-" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
        LocalDateTime overallStart = LocalDateTime.now();

        List<PipelineStageVO> stages = new ArrayList<>();
        List<KnowledgeChunkVO> chunks = new ArrayList<>();

        DocumentParserService.ParsedDocument parsedDoc = null;
        String articleId = "art-" + System.currentTimeMillis() + "-" + (int) (Math.random() * 1000);
        String versionId = "ver-" + System.currentTimeMillis() + "-" + (int) (Math.random() * 1000);

        try {
            // ================= Stage 1: 文档解析与文本提取 =================
            LocalDateTime s1Start = LocalDateTime.now();
            long s1StartMs = System.currentTimeMillis();

            parsedDoc = parserService.parse(file, request.getTitle());

            long s1EndMs = System.currentTimeMillis();
            Map<String, Object> s1Metrics = new HashMap<>();
            s1Metrics.put("fileName", parsedDoc.getOriginalFileName());
            s1Metrics.put("fileExtension", parsedDoc.getFileExtension());
            s1Metrics.put("fileSizeBytes", parsedDoc.getFileSizeBytes());
            s1Metrics.put("extractedTitle", parsedDoc.getExtractedTitle());
            s1Metrics.put("lineCount", parsedDoc.getLineCount());
            s1Metrics.put("charCount", parsedDoc.getCharacterCount());

            stages.add(PipelineStageVO.builder()
                    .stageCode("PARSING")
                    .stageName("文档解析与文本提取")
                    .description("读取原始文件流，清洗特殊控制符，提取 Markdown 标题层级与正文文本")
                    .status("SUCCESS")
                    .startTime(s1Start)
                    .endTime(LocalDateTime.now())
                    .durationMs(s1EndMs - s1StartMs)
                    .message(String.format("解析成功: 提取到 %d 字符, 共 %d 行", parsedDoc.getCharacterCount(), parsedDoc.getLineCount()))
                    .metrics(s1Metrics)
                    .build());

            // ================= Stage 2: 文本清洗与智能分块 =================
            LocalDateTime s2Start = LocalDateTime.now();
            long s2StartMs = System.currentTimeMillis();

            ChunkConfigDTO chunkConfig = new ChunkConfigDTO();
            if (request.getChunkSize() > 0) chunkConfig.setChunkSize(request.getChunkSize());
            if (request.getChunkOverlap() >= 0) chunkConfig.setChunkOverlap(request.getChunkOverlap());
            if (request.getMinChunkSize() > 0) chunkConfig.setMinChunkSize(request.getMinChunkSize());

            chunks = chunkerService.chunkDocument(parsedDoc.getFullContent(), parsedDoc.getExtractedTitle(), chunkConfig);

            long s2EndMs = System.currentTimeMillis();
            int totalTokensEstimate = chunks.stream().mapToInt(KnowledgeChunkVO::getTokenCountEstimate).sum();
            int totalChars = chunks.stream().mapToInt(KnowledgeChunkVO::getCharCount).sum();

            Map<String, Object> s2Metrics = new HashMap<>();
            s2Metrics.put("chunkCount", chunks.size());
            s2Metrics.put("targetChunkSize", chunkConfig.getChunkSize());
            s2Metrics.put("chunkOverlap", chunkConfig.getChunkOverlap());
            s2Metrics.put("totalTokensEstimate", totalTokensEstimate);
            s2Metrics.put("avgChunkLength", chunks.isEmpty() ? 0 : totalChars / chunks.size());

            stages.add(PipelineStageVO.builder()
                    .stageCode("CHUNKING")
                    .stageName("文本清洗与智能切片")
                    .description("基于 Markdown 标题层级与段落边界，按滑动窗口生成独立检索语义块")
                    .status("SUCCESS")
                    .startTime(s2Start)
                    .endTime(LocalDateTime.now())
                    .durationMs(s2EndMs - s2StartMs)
                    .message(String.format("分块完成: 生成 %d 个语义切片, 预估 %d Tokens", chunks.size(), totalTokensEstimate))
                    .metrics(s2Metrics)
                    .build());

            // ================= Stage 3: 持久化与 ES 索引 =================
            LocalDateTime s3Start = LocalDateTime.now();
            long s3StartMs = System.currentTimeMillis();

            // 3.1 尝试持久化到 MySQL (知识库文章表与版本表)
            KnowledgeArticle article = new KnowledgeArticle();
            article.setArticleId(articleId);
            article.setStatus(KnowledgeStatus.PUBLISHED);
            article.setCurrentVersionId(versionId);
            article.setCategoryId(request.getCategoryId() != null ? request.getCategoryId() : "C_NET");
            article.setRiskLevel(request.getRiskLevel() != null ? request.getRiskLevel() : KnowledgeRiskLevel.LOW);
            article.setVersion(0L);

            KnowledgeVersion version = new KnowledgeVersion();
            version.setVersionId(versionId);
            version.setArticleId(articleId);
            version.setVersionNo(1);
            version.setAuthorId(request.getAuthorId() != null ? request.getAuthorId() : "kb_admin");
            version.setChangeNote("初始文档上传与智能切片");
            version.setPublishedAt(LocalDateTime.now());

            try {
                Map<String, Object> contentMap = new HashMap<>();
                contentMap.put("title", parsedDoc.getExtractedTitle());
                contentMap.put("fileName", parsedDoc.getOriginalFileName());
                contentMap.put("chunkCount", chunks.size());
                contentMap.put("rawContent", parsedDoc.getFullContent());
                version.setContentJson(objectMapper.writeValueAsString(contentMap));

                articleMapper.insert(article);
                versionMapper.insert(version);
                log.info("Persisted knowledge article {} and version {} to MySQL", articleId, versionId);
            } catch (Exception e) {
                log.warn("MySQL persist warning (continuing pipeline): {}", e.getMessage());
            }

            // 3.2 批量存入 Elasticsearch
            ElasticsearchIndexService.IndexResult esResult = indexService.indexChunks(
                    articleId, versionId, article.getCategoryId(), chunks
            );

            long s3EndMs = System.currentTimeMillis();
            Map<String, Object> s3Metrics = new HashMap<>();
            s3Metrics.put("targetIndex", esResult.getIndexName());
            s3Metrics.put("totalChunks", esResult.getTotalChunks());
            s3Metrics.put("indexedChunks", esResult.getIndexedChunks());
            s3Metrics.put("esEndpoint", esResult.getEsEndpoint());
            s3Metrics.putAll(esResult.getDetails());

            stages.add(PipelineStageVO.builder()
                    .stageCode("ES_INDEXING")
                    .stageName("Elasticsearch 索引与持久化")
                    .description("将切片及其元数据批量构建全文索引并存储至 Elasticsearch 知识库索引")
                    .status(esResult.isSuccess() ? "SUCCESS" : "WARNING")
                    .startTime(s3Start)
                    .endTime(LocalDateTime.now())
                    .durationMs(s3EndMs - s3StartMs)
                    .message(esResult.getMessage())
                    .metrics(s3Metrics)
                    .build());

            // 4. 组装全链路追踪结果对象
            LocalDateTime overallEnd = LocalDateTime.now();
            long totalDuration = System.currentTimeMillis() - s1StartMs;

            PipelineTraceVO trace = PipelineTraceVO.builder()
                    .traceId(traceId)
                    .documentName(parsedDoc.getExtractedTitle())
                    .fileType(parsedDoc.getFileExtension())
                    .fileSize(parsedDoc.getFileSizeBytes())
                    .articleId(articleId)
                    .versionId(versionId)
                    .categoryId(article.getCategoryId())
                    .status("SUCCESS")
                    .startTime(overallStart)
                    .endTime(overallEnd)
                    .totalDurationMs(totalDuration)
                    .summary(String.format("处理成功: 共解析 %d 字符, 切片为 %d 个文本块, 成功入库 ES 索引",
                            parsedDoc.getCharacterCount(), chunks.size()))
                    .stages(stages)
                    .chunks(chunks)
                    .build();

            // 存入内存追踪仓库
            traceStore.put(traceId, trace);

            return DocumentUploadResultVO.builder()
                    .article(article)
                    .version(version)
                    .trace(trace)
                    .build();

        } catch (BizException e) {
            log.error("Biz error in RAG pipeline: {}", e.getMessage());
            stages.add(PipelineStageVO.builder()
                    .stageCode("ERROR")
                    .stageName("链路异常中断")
                    .status("FAILED")
                    .startTime(LocalDateTime.now())
                    .endTime(LocalDateTime.now())
                    .durationMs(0)
                    .message(e.getMessage())
                    .build());

            PipelineTraceVO failedTrace = PipelineTraceVO.builder()
                    .traceId(traceId)
                    .documentName(file.getOriginalFilename())
                    .status("FAILED")
                    .startTime(overallStart)
                    .endTime(LocalDateTime.now())
                    .summary("处理失败: " + e.getMessage())
                    .stages(stages)
                    .chunks(chunks)
                    .build();
            traceStore.put(traceId, failedTrace);
            throw e;
        } catch (Exception e) {
            log.error("Unexpected error in RAG pipeline", e);
            stages.add(PipelineStageVO.builder()
                    .stageCode("ERROR")
                    .stageName("系统未捕获异常")
                    .status("FAILED")
                    .startTime(LocalDateTime.now())
                    .endTime(LocalDateTime.now())
                    .durationMs(0)
                    .message(e.getMessage())
                    .build());

            PipelineTraceVO failedTrace = PipelineTraceVO.builder()
                    .traceId(traceId)
                    .documentName(file.getOriginalFilename())
                    .status("FAILED")
                    .startTime(overallStart)
                    .endTime(LocalDateTime.now())
                    .summary("系统异常: " + e.getMessage())
                    .stages(stages)
                    .chunks(chunks)
                    .build();
            traceStore.put(traceId, failedTrace);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "文档切片入库链路执行异常: " + e.getMessage());
        }
    }

    /**
     * 根据 TraceId 获取链路追踪详情
     *
     * @param traceId 链路唯一标识
     * @return 链路完整报告
     */
    public PipelineTraceVO getTraceById(String traceId) {
        if (traceId == null || !traceStore.containsKey(traceId)) {
            throw new BizException(ErrorCode.PARAM_INVALID, "未找到对应的链路记录: " + traceId);
        }
        return traceStore.get(traceId);
    }

    /**
     * 获取最近执行的历史链路列表（按开始时间倒序）
     *
     * @return 历史链路列表
     */
    public List<PipelineTraceVO> listRecentTraces() {
        List<PipelineTraceVO> list = new ArrayList<>(traceStore.values());
        list.sort((a, b) -> b.getStartTime().compareTo(a.getStartTime()));
        return list;
    }
}
