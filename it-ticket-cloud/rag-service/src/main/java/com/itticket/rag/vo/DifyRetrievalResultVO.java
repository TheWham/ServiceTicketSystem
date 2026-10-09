package com.itticket.rag.vo;

import lombok.Builder;
import lombok.Data;

import java.util.List;

/**
 * Dify 混合召回结果 VO。
 */
@Data
@Builder
public class DifyRetrievalResultVO {

    /** 检索问题（回显 Dify 侧 query） */
    private String query;

    /** 实际使用的检索方式 */
    private String searchMethod;

    /** 目标知识库 ID */
    private String datasetId;

    /** 召回分段列表（按 Dify 返回顺序） */
    private List<Record> records;

    @Data
    @Builder
    public static class Record {
        private String segmentId;
        private Integer position;
        private String documentId;
        private String documentName;
        private String content;
        private List<String> keywords;
        private Double score;
        private String hitCountingMethod;
    }
}
