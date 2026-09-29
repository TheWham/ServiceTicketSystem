package com.itticket.rag.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * ============================================================================
 * RAG 检索请求 (RagRetrievalRequest)
 * ============================================================================
 *
 * <p>供 AI 客服服务对接：传入用户问题，返回已发布知识的 Top-K 切片与策略判定结果。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Data
public class RagRetrievalRequest {

    /** 用户问题或检索关键词（必填，最长 8000，与契约 AI-004.2 一致） */
    @NotBlank
    @Size(max = 8000)
    private String question;

    /** 可选：按知识分类过滤 */
    @Size(max = 64)
    private String categoryId;

    /** 可选：返回条数，默认取配置 topK，上限 maxTopK */
    private Integer topK;
}
