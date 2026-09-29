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
import com.itticket.rag.support.EsQueryDsl;
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
    private final EmbeddingClientService embeddingService;
    private final ElasticsearchIndexService indexService;
    private final KnowledgeArticleMapper articleMapper;
    private final KnowledgeVersionMapper versionMapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 内存中缓存最近处理的链路追踪记录 (Key: traceId, Value: PipelineTraceVO) */
    private final Map<String, PipelineTraceVO> traceStore = new ConcurrentHashMap<>();

    /**
     * 处理文档上传并执行 RAG 切片、向量化与入库完整链路
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
                    .description("读取原始文件流，清洗特殊控制符与 BOM，提取 Markdown 标题层级与正文文本")
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

            // ================= Stage 3: 向量嵌入计算 (Vector Embedding) =================
            LocalDateTime s3Start = LocalDateTime.now();
            long s3StartMs = System.currentTimeMillis();

            List<String> chunkTexts = chunks.stream().map(KnowledgeChunkVO::getContent).toList();
            EmbeddingClientService.EmbeddingResult embeddingRes = embeddingService.generateEmbeddings(chunkTexts);

            // 将计算出的密集向量附加到各切片实体中
            List<List<Float>> vectors = embeddingRes.getVectors();
            for (int i = 0; i < chunks.size(); i++) {
                if (i < vectors.size()) {
                    chunks.get(i).setVector(vectors.get(i));
                    chunks.get(i).setHasVector(true);
                    chunks.get(i).setVectorDimensions(embeddingRes.getDimensions());
                    chunks.get(i).setStatus("EMBEDDED");
                }
            }

            long s3EndMs = System.currentTimeMillis();
            Map<String, Object> s3Metrics = new HashMap<>();
            s3Metrics.put("embeddingModel", embeddingRes.getModel());
            s3Metrics.put("dimensions", embeddingRes.getDimensions());
            s3Metrics.put("totalTokensUsed", embeddingRes.getTotalTokens());
            s3Metrics.put("batchCount", embeddingRes.getBatchCount());
            s3Metrics.put("vectorCount", vectors.size());
            s3Metrics.put("embeddingDurationMs", s3EndMs - s3StartMs);

            stages.add(PipelineStageVO.builder()
                    .stageCode("VECTOR_EMBEDDING")
                    .stageName("向量嵌入计算 (Embedding)")
                    .description("调用百炼/Maas 向量模型生成 1024 维密集语义向量 (Dense Vector)")
                    .status("SUCCESS")
                    .startTime(s3Start)
                    .endTime(LocalDateTime.now())
                    .durationMs(s3EndMs - s3StartMs)
                    .message(String.format("向量化完成: 生成 %d 组 %d 维密集向量, 消耗 %d Tokens, 耗时 %dms",
                            vectors.size(), embeddingRes.getDimensions(), embeddingRes.getTotalTokens(), s3EndMs - s3StartMs))
                    .metrics(s3Metrics)
                    .build());

            // ================= Stage 4: 持久化与 ES 向量索引 (ES Indexing) =================
            LocalDateTime s4Start = LocalDateTime.now();
            long s4StartMs = System.currentTimeMillis();

            // 4.1 持久化到 MySQL (知识库文章表与版本表)
            // publishNow=false 时按标准生命周期落 DRAFT，等待提审与发布（SM-KNOWLEDGE-001）
            boolean publishNow = request.isPublishNow();
            KnowledgeStatus initialStatus = publishNow ? KnowledgeStatus.PUBLISHED : KnowledgeStatus.DRAFT;

            KnowledgeArticle article = new KnowledgeArticle();
            article.setArticleId(articleId);
            article.setStatus(initialStatus);
            article.setCurrentVersionId(versionId);
            article.setCategoryId(request.getCategoryId() != null ? request.getCategoryId() : "C_NET");
            article.setRiskLevel(KnowledgeRiskLevel.normalize(request.getRiskLevel()));
            article.setCreatedAt(LocalDateTime.now());
            article.setUpdatedAt(LocalDateTime.now());

            KnowledgeVersion version = new KnowledgeVersion();
            version.setVersionId(versionId);
            version.setArticleId(articleId);
            version.setVersionNo(1);
            String docTitle = parsedDoc.getExtractedTitle();
            if (docTitle != null && docTitle.length() > 100) {
                docTitle = docTitle.substring(0, 100);
            }
            version.setTitle(docTitle != null && !docTitle.isBlank() ? docTitle : "未命名文档");
            version.setContent(parsedDoc.getFullContent());
            version.setAuthorId(request.getAuthorId() != null ? request.getAuthorId() : "kb_admin");
            version.setChangeNote(publishNow
                    ? "初始文档上传、智能切片与 1024 维向量化"
                    : "初始文档上传并落为草稿，待提审发布");
            // 仅正式发布才记录生效时间；草稿态 publishedAt 保持空（PRD §16.3）
            version.setPublishedAt(publishNow ? LocalDateTime.now() : null);
            version.setCreatedAt(LocalDateTime.now());

            try {
                Map<String, Object> contentMap = new HashMap<>();
                contentMap.put("title", parsedDoc.getExtractedTitle());
                contentMap.put("fileName", parsedDoc.getOriginalFileName());
                contentMap.put("chunkCount", chunks.size());
                contentMap.put("embeddingModel", embeddingRes.getModel());
                contentMap.put("dimensions", embeddingRes.getDimensions());
                contentMap.put("rawContent", parsedDoc.getFullContent());
                version.setContentJson(objectMapper.writeValueAsString(contentMap));

                articleMapper.insert(article);
                versionMapper.insert(version);
                log.info("Persisted knowledge article {} and version {} to MySQL successfully", articleId, versionId);
            } catch (Exception e) {
                log.warn("MySQL persist warning (continuing pipeline): {}", e.getMessage(), e);
            }

            // 4.2 批量存入 Elasticsearch (包含 content、title、dense_vector 向量)
            ElasticsearchIndexService.IndexResult esResult;
            if (publishNow) {
                esResult = indexService.indexChunks(articleId, versionId, article.getCategoryId(),
                        article.getRiskLevel(), EsQueryDsl.STATUS_PUBLISHED, chunks);
            } else {
                // AI-001：未发布内容不得进入检索索引，草稿只落库不写 ES
                esResult = indexService.skippedResult("草稿态未写入 ES，待审核发布后由发布流程建立索引");
                log.info("Draft article {} kept out of ES index (publishNow=false)", articleId);
            }

            long s4EndMs = System.currentTimeMillis();
            Map<String, Object> s4Metrics = new HashMap<>();
            s4Metrics.put("targetIndex", esResult.getIndexName());
            s4Metrics.put("totalChunks", esResult.getTotalChunks());
            s4Metrics.put("indexedChunks", esResult.getIndexedChunks());
            s4Metrics.put("esEndpoint", esResult.getEsEndpoint());
            s4Metrics.putAll(esResult.getDetails());

            stages.add(PipelineStageVO.builder()
                    .stageCode("ES_INDEXING")
                    .stageName("Elasticsearch 向量索引与持久化")
                    .description("将切片文本及其 1024 维 Dense Vector 写入 Elasticsearch 索引")
                    .status(publishNow ? (esResult.isSuccess() ? "SUCCESS" : "WARNING") : "SKIPPED")
                    .startTime(s4Start)
                    .endTime(LocalDateTime.now())
                    .durationMs(s4EndMs - s4StartMs)
                    .message(esResult.getMessage())
                    .metrics(s4Metrics)
                    .build());

            // 5. 组装全链路追踪结果对象
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
                    .summary(publishNow
                            ? String.format("处理成功: 共解析 %d 字符, 生成 %d 块切片与 1024 维向量, 成功入库 ES 索引",
                                    parsedDoc.getCharacterCount(), chunks.size())
                            : String.format("处理成功: 共解析 %d 字符, 生成 %d 块切片与 1024 维向量, 已落为草稿(DRAFT)待提审发布",
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
     * 切片 + 向量化结果（上传通道与发布通道共用）
     *
     * @param chunks              已带向量的切片列表
     * @param model               实际调用的向量模型
     * @param dimensions          向量维度
     * @param totalTokens         向量化消耗 Token 总数
     * @param batchCount          批处理调用次数
     * @param embeddingDurationMs 向量化耗时
     */
    public record ChunkEmbedResult(
            List<KnowledgeChunkVO> chunks,
            String model,
            int dimensions,
            int totalTokens,
            int batchCount,
            long embeddingDurationMs) {
    }

    /**
     * 文本切片 + 向量嵌入（上传通道与知识发布通道共用的核心能力）。
     *
     * <p>发布通道（PENDING_REVIEW ➔ PUBLISHED）复用本方法，保证草稿上传与正式发布
     * 走同一套切片/向量逻辑，避免两处实现漂移。</p>
     *
     * @param title   文档标题（用于切片继承的章节标题）
     * @param content 文档正文
     * @param config  切片配置
     */
    public ChunkEmbedResult chunkAndEmbed(String title, String content, ChunkConfigDTO config) {
        List<KnowledgeChunkVO> chunks = chunkerService.chunkDocument(content, title, config);

        long startMs = System.currentTimeMillis();
        List<String> chunkTexts = chunks.stream().map(KnowledgeChunkVO::getContent).toList();
        EmbeddingClientService.EmbeddingResult embeddingRes = embeddingService.generateEmbeddings(chunkTexts);
        long durationMs = System.currentTimeMillis() - startMs;

        List<List<Float>> vectors = embeddingRes.getVectors();
        for (int i = 0; i < chunks.size(); i++) {
            if (i < vectors.size()) {
                chunks.get(i).setVector(vectors.get(i));
                chunks.get(i).setHasVector(true);
                chunks.get(i).setVectorDimensions(embeddingRes.getDimensions());
                chunks.get(i).setStatus("EMBEDDED");
            }
        }

        return new ChunkEmbedResult(chunks, embeddingRes.getModel(), embeddingRes.getDimensions(),
                embeddingRes.getTotalTokens(), embeddingRes.getBatchCount(), durationMs);
    }

    /**
     * 按知识版本正文重建检索索引（发布、以及 ES 侧补偿重建时调用）。
     *
     * @param article   知识文章
     * @param version   待索引版本
     * @param chunkSize 目标切片字符数
     * @return ES 索引执行结果
     */
    public ElasticsearchIndexService.IndexResult indexVersion(KnowledgeArticle article, KnowledgeVersion version,
                                                             int chunkSize) {
        ChunkConfigDTO config = new ChunkConfigDTO();
        if (chunkSize > 0) {
            config.setChunkSize(chunkSize);
        }
        ChunkEmbedResult embedResult = chunkAndEmbed(version.getTitle(), version.getContent(), config);
        log.info("Rebuilt {} chunks for article {} version {} before ES indexing",
                embedResult.chunks().size(), article.getArticleId(), version.getVersionId());
        return indexService.indexChunks(
                article.getArticleId(),
                version.getVersionId(),
                article.getCategoryId(),
                article.getRiskLevel(),
                EsQueryDsl.STATUS_PUBLISHED,
                embedResult.chunks());
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
