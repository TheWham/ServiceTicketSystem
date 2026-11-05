package com.itticket.consultation.controller;

import com.itticket.consultation.adapter.cache.CacheStats;
import com.itticket.consultation.adapter.cache.SemanticAnswerCache;
import com.itticket.consultation.api.ApiEnvelope;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.service.AuthzService;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 语义答案缓存的只读运维端点(RD-010:不引入额外写路径)。
 *
 * <p>只导出命中/未命中/依赖失败/驱逐等运营计数,不暴露缓存条目内容本身;
 * 面向平台管理员的经济观测面,失败三态按 AGENTS 约定严格区分计数,不静默。
 */
@Validated
@RestController
@RequestMapping("/api/v1/consultations/ai/cache")
@RequiredArgsConstructor
public class AiCacheAdminController {

    private final AuthzService authzService;
    private final SemanticAnswerCache cache;

    /** 缓存经济指标导出(hits/realMisses/depFailures/evictions/hitRate/recentSimilarities)。 */
    @GetMapping("/export")
    public ApiEnvelope<CacheStats> export() {
        authzService.requirePlatformAdmin(authzService.currentUser());
        return ApiEnvelope.ok(cache.stats(), RequestContext.get());
    }
}
