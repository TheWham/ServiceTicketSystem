package com.itticket.rag.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * Dify 纯文本文档创建请求。
 */
@Data
public class DifyTextDocumentRequest {

    /** 文档名称（Dify 侧展示名） */
    @NotBlank(message = "name 不能为空")
    private String name;

    /** 文档正文 */
    @NotBlank(message = "text 不能为空")
    private String text;

    /** 自定义切片 token 数；&lt;=0 使用 Dify 自动分段 */
    private Integer chunkSize;

    /** 切片重叠 token 数 */
    private Integer chunkOverlap;

    /** 请求内等待索引完成的最长秒数；0 表示立即返回不等 */
    private Integer waitSeconds;
}
