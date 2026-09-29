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
 * 1. GET  /api/v1/knowledge/search                     : 已发布知识检索（AI-API-005，只返回 PUBLISHED）
 * 2. GET  /api/v1/knowledge/articles                   : 知识分页列表（管理端）
 * 3. GET  /api/v1/knowledge/articles/{id}              : 知识详情（文章 + 当前版本 + 流转审计）
 * 4. POST /api/v1/knowledge/articles/{id}/submit       : 提交审核（DRAFT ➔ PENDING_REVIEW）
 * 5. POST /api/v1/knowledge/articles/{id}/publish      : 审核通过并发布（PENDING_REVIEW ➔ PUBLISHED，联动 ES 入库）
 * 6. POST /api/v1/knowledge/articles/{id}/reject       : 驳回（PENDING_REVIEW ➔ DRAFT，原因必填）
 * 7. POST /api/v1/knowledge/articles/{id}/offline      : 下线（PUBLISHED ➔ OFFLINE，联动 ES 状态同步）
 * 8. POST /api/v1/knowledge/articles/{id}/reindex      : RAG 索引补偿重建
 * 9. POST /api/v1/knowledge/articles/{id}/es-chunks/purge : 显式物理清理 ES 切片（仅平台管理员）
 * 10. POST /api/v1/knowledge/admin/backfill-index-status  : 存量切片 status 回填（严格过滤上线前置）
 *
 * 【契约规范说明】：
 * - 操作者身份来自网关透传的认证上下文，不接受请求体传入（AI-002）。
 * - 已发布知识对全体员工可见可搜索（PRD §16.6）；管理动作按角色守卫（SM-ROLE-001）。
 * - 已发布知识不得物理删除，只允许下线/新版本/回滚（PRD §16.4），故 purge 端点独立且限平台管理员。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/knowledge")
@RequiredArgsConstructor
public class KnowledgeArticleController {

    private final KnowledgeLifecycleService lifecycleService;
    private final ElasticsearchIndexService indexService;
    private final KnowledgeStore knowledgeStore;
    private final KnowledgeArticleMapper articleMapper;
    private final KnowledgeTransitionMapper transitionMapper;

    /** 已发布知识检索 —— 契约 AI-005 (AI-API-005) */
    @GetMapping("/search")
    public Result<KnowledgeSearchResponse> search(
            @RequestParam(value = "query", required = false) String query,
            @RequestParam(value = "category", required = false) String category,
            @RequestParam(value = "page", required = false, defaultValue = "1") int page,
            @RequestParam(value = "pageSize", required = false, defaultValue = "10") int pageSize) {
        UserContext.get();
        log.info("Knowledge search: query={}, category={}, page={}, pageSize={}", query, category, page, pageSize);
        return Result.ok(indexService.searchPublishedArticles(query, category, page, pageSize));
    }

    /** 知识分页列表（管理端：草稿/待审/已发布/下线全量可查） */
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

    /** 知识详情：文章 + 当前版本 + 流转审计 */
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

    /** 提交审核：DRAFT ➔ PENDING_REVIEW */
    @PostMapping("/articles/{id}/submit")
    public Result<KnowledgeLifecycleResult> submit(@PathVariable("id") String id,
                                                   @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireSubmitRole();
        log.info("Knowledge submit review: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.submitForReview(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getRemark()));
    }

    /** 审核通过并发布：PENDING_REVIEW ➔ PUBLISHED（守卫：作者不得自审 / 高风险须平台管理员复核） */
    @PostMapping("/articles/{id}/publish")
    public Result<KnowledgeLifecycleResult> publish(@PathVariable("id") String id,
                                                    @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge publish: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.publish(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getChangeNote()));
    }

    /** 驳回：PENDING_REVIEW ➔ DRAFT（原因必填） */
    @PostMapping("/articles/{id}/reject")
    public Result<KnowledgeLifecycleResult> reject(@PathVariable("id") String id,
                                                   @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge reject: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.reject(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getReason()));
    }

    /** 下线：PUBLISHED ➔ OFFLINE（原因必填，同步刷新搜索与 RAG 索引，AC-27） */
    @PostMapping("/articles/{id}/offline")
    public Result<KnowledgeLifecycleResult> offline(@PathVariable("id") String id,
                                                    @RequestBody(required = false) KnowledgeLifecycleRequest request) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge offline: articleId={}, operator={}, role={}", id, user.getUserId(), user.getRole());
        return Result.ok(lifecycleService.offline(id, user.getUserId(), Roles.normalize(user.getRole()),
                request == null ? null : request.getReason()));
    }

    /** RAG 索引补偿重建（发布后索引失败、或 ES 曾不可用时的补偿入口，RD-008） */
    @PostMapping("/articles/{id}/reindex")
    public Result<KnowledgeLifecycleResult> reindex(@PathVariable("id") String id) {
        UserContext.CurrentUser user = requireManageRole();
        log.info("Knowledge reindex: articleId={}, operator={}", id, user.getUserId());
        return Result.ok(lifecycleService.reindex(id));
    }

    /**
     * 显式物理清理该文章的 ES 切片（仅平台管理员）。
     *
     * <p>业务下线只做逻辑标记，本端点用于数据修复；不进入任何业务链路（PRD §16.4）。</p>
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
     * <p>严格状态过滤上线的前置动作，否则历史切片在检索中不可见（AC-27 相关）。</p>
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

    /** 提交审核：知识库管理员 / 平台管理员 / 工程师（SM-KNOWLEDGE-001） */
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
