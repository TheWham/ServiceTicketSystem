package com.itticket.rag.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

/**
 * Dify 召回检索请求。
 */
@Data
public class DifyRetrievalRequest {

    /** 检索问题 */
    @NotBlank(message = "query 不能为空")
    private String query;

    /** 检索方式：hybrid_search / semantic_search / full_text_search；空则取服务端默认 */
    @Pattern(regexp = "^(hybrid_search|semantic_search|full_text_search)$",
            message = "searchMethod 仅支持 hybrid_search / semantic_search / full_text_search")
    private String searchMethod;

    /** 召回条数；&lt;=0 取服务端默认 */
    private Integer topK;

    /** 分数阈值（0~1）；null 取服务端默认 */
    private Double scoreThreshold;
}
