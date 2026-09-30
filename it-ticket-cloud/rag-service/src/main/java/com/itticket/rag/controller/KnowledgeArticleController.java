package com.itticket.rag.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.rag.dto.KnowledgeLifecycleRequest;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeTransition;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import com.itticket.rag.mapper.KnowledgeTransitionMapper;
import com.itticket.rag.service.ElasticsearchIndexService;
import com.itticket.rag.service.KnowledgeLifecycleService;
import com.itticket.rag.service.KnowledgeStore;
import com.itticket.rag.support.Roles;
import com.itticket.rag.vo.KnowledgeDetail;
import com.itticket.rag.vo.KnowledgeLifecycleResult;
import com.itticket.rag.vo.KnowledgeSearchResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * ============================================================================
 * 知识生命周期与检索 HTTP 控制器 (KnowledgeArticleController)
 * ============================================================================
 *
 * 【接口列表】：
 * 1. GET  /api/v1/rag/articles                       : 知识分页列表（管理端）
 * 2. GET  /api/v1/rag/articles/{id}                  : 知识详情（文章 + 当前版本 + 流转审计）
 * 3. POST /api/v1/rag/articles/{id}/submit           : 提交审核（DRAFT ➔ PENDING_REVIEW）
 * 4. POST /api/v1/rag/articles/{id}/publish          : 审核通过并发布（PENDING_REVIEW ➔ PUBLISHED，联动 ES 入库）
 * 5. POST /api/v1/rag/articles/{id}/reject           : 驳回（PENDING_REVIEW ➔ DRAFT，原因必填）
 * 6. POST /api/v1/rag/articles/{id}/offline          : 下线（PUBLISHED ➔ OFFLINE，联动 ES 状态同步）
 * 7. POST /api/v1/rag/articles/{id}/reindex          : RAG 索引补偿重建
 * 8. POST /api/v1/rag/articles/{id}/es-chunks/purge  : 显式物理清理 ES 切片（仅平台管理员）
 * 9. POST /api/v1/rag/admin/backfill-index-status    : 存量切片 status 回填（严格过滤上线前置）
 *
 * 【职责边界】：
 * - 本控制器只负责知识生命周期与 RAG 索引联动（SM-KNOWLEDGE-001 / AC-27）。
 * - AI 消息（AI-API-002）与已发布知识搜索（AI-API-005）由 AI 客服服务（consultation-service）
 *   在 /api/v1/consultations/** 与 /api/v1/knowledge/** 下实现，本模块不重复提供。
 *
 * 【规范引用】（路径相对仓库根目录 docs/）：
 * - SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90
 *     知识四态状态机 DRAFT ➔ PENDING_REVIEW ➔ PUBLISHED ➔ OFFLINE 及各迁移守卫。
 * - SM-001 · specs/03-business-state-machine.md:12
 *     每次状态迁移追加 knowledge_transition 审计记录，历史不可覆盖。
 * - AC-25 · specs/09-prd-spec-test-traceability.md:91
 *     作者不得审核自己提交的内容（发布守卫）。
 * - AC-27 · specs/09-prd-spec-test-traceability.md:93
 *     知识下线后页面搜索与 RAG 检索均不再返回该版本。
 * - PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515
 *     高风险知识须平台管理员复核；已发布知识不物理删除，只允许下线/新版本/回滚。
 * - PRD §5.1 · IT服务工单系统PRD-Ultimate.md:89
 *     角色值域（KNOWLEDGE_ADMIN / PLATFORM_ADMIN / ENGINEER）。
 * - RD-006 / RD-008 · specs/04-resilience-degradation.md:67 / :93
 *     索引失败不回滚已合法状态，走补偿入口（reindex）。
 * - AI-004.4 / AI-API-005 · specs/02-ai-api-json-schema.md:174 / :257
 *     契约知识搜索接口（GET /api/v1/knowledge/search）由 AI 客服服务提供；
 *     本模块 /articles/search 仅为核对 ES 内容的运维等价视图，不是对外契约路径。
 * - AI-002 · specs/02-ai-api-json-schema.md:25
 *     操作者身份来自网关透传的认证上下文，不信任请求体。
 *
 * 【角色守卫】：
 * - 管理动作按角色守卫：知识库管理员 KNOWLEDGE_ADMIN / 平台管理员 PLATFORM_ADMIN，
 *   角色值域兼容网关历史上的小写出口与 KB_ADMIN 别名（见 support/Roles.java）。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/rag")
@RequiredArgsConstructor
public class KnowledgeArticleController {

    private final KnowledgeLifecycleService lifecycleService;
    private final ElasticsearchIndexService indexService;
    private final KnowledgeStore knowledgeStore;
    private final KnowledgeArticleMapper articleMapper;
    private final KnowledgeTransitionMapper transitionMapper;

    /**
     * ES 原生文章检索（运维/验收视图，只返回 status=PUBLISHED）。
     *
     * <p>契约路径 {@code GET /api/v1/knowledge/search}（AI-API-005 · specs/02-ai-api-json-schema.md:257，
     * 响应形态 AI-004.4 · :174）由 AI 客服服务提供；本端点是 rag-service 侧的等价检索能力，
     * 用于核对 ES 索引内容与下线联动（AC-27 · specs/09-prd-spec-test-traceability.md:93），
     * 供运维与验收使用，不作为对外契约路径。响应字段对齐 AI-004.4：
     * articleId / versionId / title / summary / categoryId + 分页元数据。</p>
     */
    @GetMapping("/articles/search")
    public Result<KnowledgeSearchResponse> searchArticles(
            @RequestParam(value = "query", required = false) String query,
            @RequestParam(value = "category", required = false) String category,
            @RequestParam(value = "page", required = false, defaultValue = "1") int page,
            @RequestParam(value = "pageSize", required = false, defaultValue = "10") int pageSize) {
        UserContext.get();
        log.info("ES article search: query={}, category={}, page={}, pageSize={}", query, category, page, pageSize);
        return Result.ok(indexService.searchPublishedArticles(query, category, page, pageSize));
    }

    /** 知识分页列表（管理端：草稿/待审/已发布/下线全量可查，状态值域见 SM-KNOWLEDGE-001） */
    @GetMapping("/articles")
    public Result<Page<KnowledgeArticle>> listArticles(
            @RequestParam(value = "status", required = false) String status,
            @RequestParam(value = "category", required = false) String category,
            @RequestParam(value = "page", required = false, defaultValue = "1") int page,
            @RequestParam(value = "pageSize", required = false, defaultValue = "10") int pageSize) {
        UserContext.get();
        Page<KnowledgeArticle> pageRequest = new Page<>(Math.max(1, page), Math.min(Math.max(1, pageSize), 100));
        LambdaQueryWrapper<KnowledgeArticle> wrapper = new LambdaQueryWrapper<KnowledgeArticle>()
                .eq(StringUtils.hasText(status), KnowledgeArticle::getStatus, status)
                .eq(StringUtils.hasText(category), KnowledgeArticle::getCategoryId, category)
                .orderByDesc(KnowledgeArticle::getUpdatedAt);
        return Result.ok(articleMapper.selectPage(pageRequest, wrapper));
    }

    /** 知识详情：文章 + 当前版本 + 流转审计时间线（审计要求 SM-001 · specs/03-business-state-machine.md:12） */
    @GetMapping("/articles/{id}")
    public Result<KnowledgeDetail> detail(@PathVariable("id") String id) {
        UserContext.get();
        KnowledgeArticle article = knowledgeStore.requireArticle(id);
        List<KnowledgeTransition> transitions = transitionMapper.selectList(
                new LambdaQueryWrapper<KnowledgeTransition>()
                        .eq(KnowledgeTransition::getArticleId, id)
                        .orderByAsc(KnowledgeTransition::getOccurredAt));
        return Result.ok(new KnowledgeDetail(article,
                article.getCurrentVersionId() == null ? null
                        : knowledgeStore.requireCurrentVersion(article),
                transitions));
    }

    /**
     * 提交审核：DRAFT ➔ PENDING_REVIEW。
     *
     * <p>SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90：
     * 允许角色为知识库管理员/工程师；守卫「已脱敏，结构化字段完整」。</p>
     */
    @PostMapping("/articles/{id}/submit")
    public Result<KnowledgeLifecycleResult> submit(@PathVariable("id") String id,
                                                   @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireSubmitRole();
        log.info("Knowledge submit review: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.submitForReview(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getRemark()));
    }

    /**
     * 审核通过并发布：PENDING_REVIEW ➔ PUBLISHED。
     *
     * <p>守卫（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90）：</p>
     * <ul>
     *   <li>作者不得自审（AC-25 · specs/09-prd-spec-test-traceability.md:91）；</li>
     *   <li>高风险知识须平台管理员复核（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515）。</li>
     * </ul>
     * <p>发布成功后在事务外联动 ES 切片入库；索引失败不回滚状态，标记
     * PENDING_COMPENSATION 走 reindex 补偿（RD-006/RD-008 · specs/04-resilience-degradation.md:67/:93）。</p>
     */
    @PostMapping("/articles/{id}/publish")
    public Result<KnowledgeLifecycleResult> publish(@PathVariable("id") String id,
                                                    @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge publish: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.publish(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getChangeNote()));
    }

    /** 驳回：PENDING_REVIEW ➔ DRAFT，原因必填（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90） */
    @PostMapping("/articles/{id}/reject")
    public Result<KnowledgeLifecycleResult> reject(@PathVariable("id") String id,
                                                   @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge reject: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.reject(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getReason()));
    }

    /**
     * 下线：PUBLISHED ➔ OFFLINE，原因必填（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90）。
     *
     * <p>下线后同步刷新搜索与 RAG 索引：ES 中该文章全部切片 status 置 OFFLINE，
     * 此后检索与 AI 引用均不再返回（AC-27 · IT服务工单系统PRD-Ultimate.md:911 /
     * specs/09-prd-spec-test-traceability.md:93）。</p>
     */
    @PostMapping("/articles/{id}/offline")
    public Result<KnowledgeLifecycleResult> offline(@PathVariable("id") String id,
                                                    @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge offline: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.offline(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getReason()));
    }

    /**
     * RAG 索引补偿重建：发布后索引失败、或 ES 曾不可用时的补偿入口
     * （RD-006/RD-008 · specs/04-resilience-degradation.md:67/:93）。
     */
    @PostMapping("/articles/{id}/reindex")
    public Result<KnowledgeLifecycleResult> reindex(@PathVariable("id") String id) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge reindex: articleId={}, operator={}", id, user.getUserId());
        return Result.ok(lifecycleService.reindex(id));
    }

    /**
     * 显式物理清理该文章的 ES 切片（仅平台管理员）。
     *
     * <p>业务下线只做逻辑标记（PUBLISHED ➔ OFFLINE），已发布知识不物理删除
     * （PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515）；本端点仅用于数据修复，
     * 不进入任何业务链路。</p>
     */
    @PostMapping("/articles/{id}/es-chunks/purge")
    public Result<Map<String, Object>> purgeEsChunks(@PathVariable("id") String id) {
        UserContext.CurrentUser user = requirePlatformAdmin();
        log.warn("ES chunks purge requested: articleId={}, operator={}", id, user.getUserId());
        long deleted = lifecycleService.purgeEsChunks(id);
        Map<String, Object> data = new HashMap<>();
        data.put("articleId", id);
        data.put("deleted", deleted);
        data.put("success", deleted >= 0);
        return Result.ok(data);
    }

    /**
     * 存量切片 status 回填：把缺少 status 的历史切片补为 PUBLISHED。
     *
     * <p>严格状态过滤上线的前置动作：不先回填，历史切片在检索中全部不可见
     * （AI-001 只读 PUBLISHED · specs/02-ai-api-json-schema.md:14；
     * AC-27 · specs/09-prd-spec-test-traceability.md:93）。</p>
     */
    @PostMapping("/admin/backfill-index-status")
    public Result<Map<String, Object>> backfillIndexStatus() {
        UserContext.CurrentUser user = requireManageRole();
        log.info("ES status backfill requested by {}", user.getUserId());
        long updated = lifecycleService.backfillMissingStatus();
        Map<String, Object> data = new HashMap<>();
        data.put("updated", updated);
        data.put("indexReady", lifecycleService.ensureIndexReady());
        return Result.ok(data);
    }

    // ---------------------------------------------------------------- 角色守卫

    /** 提交审核：知识库管理员 / 平台管理员 / 工程师（SM-KNOWLEDGE-001 迁移表「提交审核」行；角色值域 PRD §5.1） */
    private UserContext.CurrentUser requireSubmitRole() {
        UserContext.CurrentUser user = UserContext.get();
        if (!Roles.canSubmitReview(user.getRole())) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要 知识库管理员、平台管理员 或 工程师 权限");
        }
        return user;
    }

    /** 审核/发布/驳回/下线：知识库管理员 / 平台管理员 */
    private UserContext.CurrentUser requireManageRole() {
        UserContext.CurrentUser user = UserContext.get();
        if (!Roles.canManageKnowledge(user.getRole())) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要 知识库管理员 或 平台管理员 权限");
        }
        return user;
    }

    /** 平台管理员专属 */
    private UserContext.CurrentUser requirePlatformAdmin() {
        UserContext.CurrentUser user = UserContext.get();
        if (!Roles.isPlatformAdmin(user.getRole())) {
            throw new BizException(ErrorCode.FORBIDDEN, "需要 平台管理员 权限");
        }
        return user;
    }
}
