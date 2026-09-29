package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.KnowledgeSearchResponse;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.KnowledgeQueryService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 知识搜索(AI-API-005)。只返回 PUBLISHED 的当前版本,不暴露来源工单。
 *
 * <p>PRD 16.6:正式发布知识面向全体员工共享,因此任何已认证角色都可搜索;
 * 是否可公开在发布审核阶段已经把关,搜索接口不再做二次可见性裁剪。
 */
@Validated
@RestController
@RequestMapping("/api/v1/knowledge")
@RequiredArgsConstructor
public class KnowledgeSearchController {

    private final KnowledgeQueryService knowledgeQueryService;
    private final AuthzService authzService;

    @GetMapping("/search")
    public ApiEnvelope<KnowledgeSearchResponse> search(
            @RequestParam(required = false) @Size(max = 200) String query,
            @RequestParam(required = false) @Size(max = 64) String category,
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int pageSize) {
        // 触发认证校验:未认证主体不得检索知识(AX-001 判定顺序第一步)
        authzService.currentUser();
        return ApiEnvelope.ok(knowledgeQueryService.search(query, category, page, pageSize),
                RequestContext.get());
    }
}
