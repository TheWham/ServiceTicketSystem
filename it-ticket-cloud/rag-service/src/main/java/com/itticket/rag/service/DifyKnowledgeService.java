package com.itticket.rag.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.config.DifyProperties;
import com.itticket.rag.dto.DifyRetrievalRequest;
import com.itticket.rag.vo.DifyDocumentUploadResultVO;
import com.itticket.rag.vo.DifyRetrievalResultVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * ============================================================================
 * Dify 知识库编排服务 (DifyKnowledgeService)
 * ============================================================================
 *
 * 【业务定位】：
 * 在既有「自研解析 ➔ 切片 ➔ Embedding ➔ ES 混合检索」链路之外，提供一条 Dify 通道：
 * 文档上传、分块、向量化与混合索引全部由 Dify 平台完成，本服务只做参数编排、
 * 状态轮询与结果映射，便于与自研链路做召回质量对比。
 *
 * 两条通道相互独立：Dify 通道不写 MySQL/ES，也不受知识生命周期状态机约束，
 * 因此不参与 /api/v1/rag/retrievals 的 PUBLISHED 校验（AI-001）。若需接入正式
 * 检索出口，应先补齐 articleId/versionId 映射，本次接入范围不含该项。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DifyKnowledgeService {

    private final DifyDatasetClient client;
    private final DifyProperties properties;

    /** 默认等待索引完成的最长秒数 */
    private static final int DEFAULT_WAIT_SECONDS = 60;
    /** 轮询间隔（毫秒） */
    private static final long POLL_INTERVAL_MS = 2000L;

    /** 启用校验：未开启 Dify 通道时直接拒绝，避免误用 */
    private void requireEnabled() {
        if (!properties.isEnabled()) {
            throw new BizException(ErrorCode.PARAM_INVALID,
                    "Dify 通道未启用：请设置 rag.dify.enabled=true 并注入 DIFY_API_KEY");
        }
    }

    /** 确保知识库存在（按名称复用，否则创建） */
    public DifyDatasetClient.Dataset ensureDataset() {
        requireEnabled();
        return client.ensureDataset();
    }

    /**
     * 上传文档到 Dify 知识库（解析/分块/向量化/混合索引均由 Dify 完成）。
     *
     * @param file         上传文件（txt/md/pdf/docx 等 Dify 支持的格式）
     * @param chunkSize    自定义切片 token 数；&lt;=0 使用 Dify 自动分段
     * @param chunkOverlap 切片重叠 token 数
     * @param waitSeconds  请求内等待索引完成的最长秒数；0 表示立即返回不等
     */
    public DifyDocumentUploadResultVO uploadDocument(MultipartFile file, int chunkSize, int chunkOverlap,
                                                     Integer waitSeconds) {
        requireEnabled();
        if (file == null || file.isEmpty()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "上传文件不能为空");
        }
        String fileName = file.getOriginalFilename();
        log.info("Dify 文档上传: name={}, size={} bytes, chunkSize={}", fileName, file.getSize(), chunkSize);

        try {
            client.ensureDataset();
            DifyDatasetClient.DocumentCreateResult created =
                    client.createDocumentByFile(fileName, file.getBytes(), chunkSize, chunkOverlap);

            DifyDocumentUploadResultVO.DifyDocumentUploadResultVOBuilder builder =
                    DifyDocumentUploadResultVO.builder()
                            .datasetId(properties.getDatasetId())
                            .batch(created.getBatch())
                            .documentId(created.getDocumentId())
                            .documentName(created.getDocumentName())
                            .indexingStatus(created.getIndexingStatus())
                            .statuses(List.of());

            int wait = waitSeconds == null ? DEFAULT_WAIT_SECONDS : Math.max(waitSeconds, 0);
            if (wait > 0) {
                List<DifyDatasetClient.IndexingStatus> statuses = waitIndexing(created.getBatch(), wait);
                builder.waited(true)
                        .statuses(statuses.stream().map(this::toItem).toList())
                        .indexingStatus(statuses.isEmpty()
                                ? created.getIndexingStatus()
                                : statuses.get(0).getIndexingStatus());
            }
            return builder.build();
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("Dify 文档上传失败: {}", e.getMessage(), e);
            throw new BizException(ErrorCode.SYSTEM_ERROR, "Dify 文档上传失败: " + e.getMessage());
        }
    }

    /**
     * 按纯文本创建 Dify 文档（无需上传文件流）。
     *
     * @param name         文档名称
     * @param text         正文
     * @param chunkSize    自定义切片 token 数；&lt;=0 使用 Dify 自动分段
     * @param chunkOverlap 切片重叠 token 数
     * @param waitSeconds  请求内等待索引完成的最长秒数；0 表示立即返回不等
     */
    public DifyDocumentUploadResultVO createDocumentByText(String name, String text, int chunkSize,
                                                           int chunkOverlap, Integer waitSeconds) {
        requireEnabled();
        if (name == null || name.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "name 不能为空");
        }
        if (text == null || text.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "text 不能为空");
        }
        client.ensureDataset();
        DifyDatasetClient.DocumentCreateResult created =
                client.createDocumentByText(name, text, chunkSize, chunkOverlap);

        DifyDocumentUploadResultVO.DifyDocumentUploadResultVOBuilder builder =
                DifyDocumentUploadResultVO.builder()
                        .datasetId(properties.getDatasetId())
                        .batch(created.getBatch())
                        .documentId(created.getDocumentId())
                        .documentName(created.getDocumentName())
                        .indexingStatus(created.getIndexingStatus())
                        .statuses(List.of());

        int wait = waitSeconds == null ? DEFAULT_WAIT_SECONDS : Math.max(waitSeconds, 0);
        if (wait > 0) {
            List<DifyDatasetClient.IndexingStatus> statuses = waitIndexing(created.getBatch(), wait);
            builder.waited(true)
                    .statuses(statuses.stream().map(this::toItem).toList())
                    .indexingStatus(statuses.isEmpty()
                            ? created.getIndexingStatus()
                            : statuses.get(0).getIndexingStatus());
        }
        return builder.build();
    }

    /** 查询批次索引状态（不等待） */
    public List<DifyDocumentUploadResultVO.Item> getIndexingStatus(String batch) {
        requireEnabled();
        return client.getIndexingStatus(batch).stream().map(this::toItem).toList();
    }

    /**
     * Dify 混合召回。
     *
     * @param request 检索请求（query 必填，searchMethod/topK/scoreThreshold 可选）
     */
    public DifyRetrievalResultVO retrieve(DifyRetrievalRequest request) {
        requireEnabled();
        client.ensureDataset();
        DifyDatasetClient.RetrieveResult result = client.retrieve(
                request.getQuery(), request.getSearchMethod(), request.getTopK(), request.getScoreThreshold());

        List<DifyRetrievalResultVO.Record> records = result.getRecords().stream()
                .map(r -> DifyRetrievalResultVO.Record.builder()
                        .segmentId(r.getSegmentId())
                        .position(r.getPosition())
                        .documentId(r.getDocumentId())
                        .documentName(r.getDocumentName())
                        .content(r.getContent())
                        .keywords(r.getKeywords())
                        .score(r.getScore())
                        .hitCountingMethod(r.getHitCountingMethod())
                        .build())
                .toList();

        String method = request.getSearchMethod() == null || request.getSearchMethod().isBlank()
                ? properties.getSearchMethod() : request.getSearchMethod();
        log.info("Dify 召回完成: query={}, method={}, hits={}", request.getQuery(), method, records.size());

        return DifyRetrievalResultVO.builder()
                .query(result.getQuery())
                .searchMethod(method)
                .datasetId(properties.getDatasetId())
                .records(records)
                .build();
    }

    /** 轮询索引状态直到 completed/error 或超时；超时不视为失败（Dify 仍在异步处理） */
    private List<DifyDatasetClient.IndexingStatus> waitIndexing(String batch, int waitSeconds) {
        long deadline = System.currentTimeMillis() + waitSeconds * 1000L;
        List<DifyDatasetClient.IndexingStatus> statuses = client.getIndexingStatus(batch);
        while (System.currentTimeMillis() < deadline && !isFinished(statuses)) {
            try {
                Thread.sleep(POLL_INTERVAL_MS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                log.warn("等待 Dify 索引被中断: batch={}", batch);
                break;
            }
            statuses = client.getIndexingStatus(batch);
        }
        return statuses;
    }

    /** 全部文档到达 completed/error 视为结束 */
    private boolean isFinished(List<DifyDatasetClient.IndexingStatus> statuses) {
        if (statuses == null || statuses.isEmpty()) {
            return false;
        }
        return statuses.stream().allMatch(s ->
                "completed".equalsIgnoreCase(s.getIndexingStatus()) || "error".equalsIgnoreCase(s.getIndexingStatus()));
    }

    private DifyDocumentUploadResultVO.Item toItem(DifyDatasetClient.IndexingStatus s) {
        return DifyDocumentUploadResultVO.Item.builder()
                .documentId(s.getDocumentId())
                .indexingStatus(s.getIndexingStatus())
                .wordCount(s.getWordCount())
                .error(s.getError())
                .build();
    }
}
