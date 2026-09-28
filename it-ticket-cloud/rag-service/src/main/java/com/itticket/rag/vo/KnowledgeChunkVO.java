package com.itticket.rag.vo;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * ============================================================================
 * 知识切片值对象 (KnowledgeChunkVO)
 * ============================================================================
 *
 * 【切片数据结构】：
 * 表达文档经过清洗分块后的独立语义检索单元，可直接用于 ES 全文检索或向量索引。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeChunkVO {
    /** 切片在文档中的自然序号 (从 1 开始递增) */
    private int chunkIndex;

    /** 切片全局唯一业务标识 (如 "chk-3a5f9e2b1c4d8a7e") */
    private String chunkId;

    /** 切片继承的所属章节标题 (如 "常见网络与VPN问题排查 > 二、VPN客户端登录错误处理") */
    private String title;

    /** 切片实际纯文本正文内容 */
    private String content;

    /** 切片字符数统计 */
    private int charCount;

    /** 切片预估消耗的 Token 数量 */
    private int tokenCountEstimate;

    /** Elasticsearch 存储文档 ID */
    private String esDocId;

    /** 1024 维密集向量数据 */
    private java.util.List<Float> vector;

    /** 是否已生成向量嵌入 */
    private Boolean hasVector;

    /** 向量维度（例如 1024） */
    private Integer vectorDimensions;

    /** 切片处理状态 (CHUNKED-已切片, EMBEDDED-已向量化, SUCCESS-已入库, FAILED-失败) */
    private String status;

    /** 异常信息 (若有) */
    private String errorMessage;
}
