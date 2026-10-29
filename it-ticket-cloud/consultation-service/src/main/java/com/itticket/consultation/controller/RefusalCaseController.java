package com.itticket.consultation.controller;

import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.PagedData;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.dto.BadCaseReviewView;
import com.itticket.consultation.dto.RefusalCaseDetail;
import com.itticket.consultation.dto.RefusalCaseItem;
import com.itticket.consultation.dto.ReviewRequest;
import com.itticket.consultation.service.AuthzService;
import com.itticket.consultation.service.CurrentUser;
import com.itticket.consultation.service.RefusalCaseService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 拒答案例管理端接口(知识库管理员)。
 *
 * <p>路径落在 /api/v1/consultations/** 网关既有路由内;字面量前缀 refusal-cases
 * 与 {@code /{sessionId}} 模板路由不冲突(Spring 精确匹配优先)。</p>
 */
@Validated
@RestController
@RequestMapping("/api/v1/consultations/refusal-cases")
@RequiredArgsConstructor
public class RefusalCaseController {

    private final RefusalCaseService refusalCaseService;
    private final AuthzService authzService;

    /** 拒答案例分页列表。status=PENDING(默认)/REVIEWED/ALL,keyword 模糊匹配提问正文。 */
    @GetMapping
    public ApiEnvelope<PagedData<RefusalCaseItem>> list(
            @RequestParam(value = "page", defaultValue = "1") @Min(1) int page,
            @RequestParam(value = "pageSize", defaultValue = "15") @Min(1) @Max(100) int pageSize,
            @RequestParam(value = "status", required = false) String status,
            @RequestParam(value = "keyword", required = false) String keyword) {
        CurrentUser user = authzService.currentUser();
        if (user.role() != com.itticket.consultation.enums.RoleCode.KNOWLEDGE_ADMIN
                && user.role() != com.itticket.consultation.enums.RoleCode.PLATFORM_ADMIN) {
            throw new com.itticket.consultation.api.ApiException(
                    com.itticket.consultation.api.ApiCode.FORBIDDEN, "需要 知识库管理员 或 平台管理员 权限");
        }
        return ApiEnvelope.ok(refusalCaseService.page(page, pageSize, status, keyword), RequestContext.get());
    }

    /** 拒答案例详情(含会话上下文)。 */
    @GetMapping("/{messageId}")
    public ApiEnvelope<RefusalCaseDetail> detail(@PathVariable("messageId") String messageId) {
        requireManageRole();
        return ApiEnvelope.ok(refusalCaseService.detail(messageId), RequestContext.get());
    }

    /** 处置:GOLDEN_QA / GOLDEN_REFUSAL(入黄金集) / DISCARD。重复处置返回 409。 */
    @PostMapping("/{messageId}/review")
    public ApiEnvelope<BadCaseReviewView> review(@PathVariable("messageId") String messageId,
                                                 @Valid @RequestBody ReviewRequest request) {
        CurrentUser user = requireManageRole();
        return ApiEnvelope.ok(refusalCaseService.review(messageId, request, user), RequestContext.get());
    }

    private CurrentUser requireManageRole() {
        CurrentUser user = authzService.currentUser();
        if (user.role() != com.itticket.consultation.enums.RoleCode.KNOWLEDGE_ADMIN
                && user.role() != com.itticket.consultation.enums.RoleCode.PLATFORM_ADMIN) {
            throw new com.itticket.consultation.api.ApiException(
                    com.itticket.consultation.api.ApiCode.FORBIDDEN, "需要 知识库管理员 或 平台管理员 权限");
        }
        return user;
    }
}
