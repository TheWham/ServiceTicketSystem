package com.itticket.rag.vo;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * Dify 文档上传结果 VO：Dify 侧异步完成解析、分块、向量化与混合索引。
 */
@Data
@Builder
public class DifyDocumentUploadResultVO {

    /** 目标知识库 ID */
    private String datasetId;

    /** 批次 ID（轮询索引状态使用） */
    private String batch;

    /** 文档 ID */
    private String documentId;

    /** 文档名称 */
    private String documentName;

    /** 创建时的索引状态（waiting/parsing/...） */
    private String indexingStatus;

    /** 是否在请求内等待索引完成 */
    private boolean waited;

    /** 等待结束后的索引状态列表（waited=false 时为空） */
    private List<Item> statuses;

    /** 单个文档的索引进度 */
    @Data
    @Builder
    public static class Item {
        private String documentId;
        private String indexingStatus;
        private Integer wordCount;
        private String error;
    }
}
