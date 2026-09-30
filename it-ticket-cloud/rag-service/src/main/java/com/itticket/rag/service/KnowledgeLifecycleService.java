package com.itticket.rag.service;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeVersion;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.support.EsQueryDsl;
import com.itticket.rag.vo.KnowledgeLifecycleResult;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * ============================================================================
 * 知识生命周期编排服务 (KnowledgeLifecycleService)
 * ============================================================================
 *
 * 【职责边界】：
 * 1. 事务内的状态迁移与守卫委托给 {@link KnowledgeStore}（SM-001 · specs/03-business-state-machine.md:12）。
 * 2. 事务提交后再执行 RAG 索引副作用，避免外部调用持有主事务数据库连接
 *    （RD-013 · specs/04-resilience-degradation.md:142）。
 * 3. 索引失败不回滚已合法状态，标记 PENDING_COMPENSATION 并可由 reindex 端点补偿
 *    （RD-006 / RD-008 · specs/04-resilience-degradation.md:67 / :93）。
 *
 * 【状态机（SM-KNOWLEDGE-001）】：
 * <pre>
 *   DRAFT --提交审核--> PENDING_REVIEW --审核通过--> PUBLISHED --下线--> OFFLINE
 *                          |                              ^
 *                          +--驳回--> DRAFT               |
 *                          （PUBLISHED/OFFLINE 发布新版本为后续轮次）
 * </pre>
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class KnowledgeLifecycleService {

    /** 索引副作用结果标记 */
    private static final String INDEXED = "INDEXED";
    private static final String PENDING_COMPENSATION = "PENDING_COMPENSATION";
    private static final String NOT_REQUIRED = "NOT_REQUIRED";

    private final KnowledgeStore store;
    private final RagPipelineService pipelineService;
    private final ElasticsearchIndexService indexService;

    /** 提交审核：DRAFT ➔ PENDING_REVIEW（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90） */
    public KnowledgeLifecycleResult submitForReview(String articleId, String operatorId, String operatorRole, String remark) {
        KnowledgeVersion version = store.submitForReview(articleId, operatorId, operatorRole, remark);
        return new KnowledgeLifecycleResult(articleId, version.getVersionId(), KnowledgeStatus.PENDING_REVIEW,
                NOT_REQUIRED, "已提交审核，等待知识库管理员审核");
    }

    /**
     * 审核通过并发布：PENDING_REVIEW ➔ PUBLISHED，并建立 RAG 索引。
     *
     * <p>守卫在事务内完成：作者不得自审（AC-25 · specs/09-prd-spec-test-traceability.md:91）、
     * 高风险须平台管理员复核（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515）。</p>
     *
     * <p>索引副作用在事务提交后执行（RD-013 · specs/04-resilience-degradation.md:142）；
     * 失败不回滚已合法状态，标记 PENDING_COMPENSATION（RD-006/RD-008）。</p>
     */
    public KnowledgeLifecycleResult publish(String articleId, String operatorId, String operatorRole, String changeNote) {
        KnowledgeVersion version = store.approveAndPublish(articleId, operatorId, operatorRole, changeNote);

        // 事务已提交，事务外执行索引副作用
        String indexStatus;
        String message;
        try {
            KnowledgeArticle article = store.requireArticle(articleId);
            ElasticsearchIndexService.IndexResult esResult = pipelineService.indexVersion(article, version, 0);
            indexStatus = isIndexed(esResult) ? INDEXED : PENDING_COMPENSATION;
            message = esResult.getMessage();
            if (!isIndexed(esResult)) {
                log.warn("知识发布后索引未真正完成，已标记待补偿: articleId={}, message={}", articleId, esResult.getMessage());
            }
        } catch (Exception e) {
            indexStatus = PENDING_COMPENSATION;
            message = "知识已发布，但 RAG 索引未完成，可调用 /articles/{id}/reindex 补偿: " + e.getMessage();
            log.error("知识发布后索引异常，已标记待补偿: articleId={}", articleId, e);
        }
        return new KnowledgeLifecycleResult(articleId, version.getVersionId(), KnowledgeStatus.PUBLISHED, indexStatus, message);
    }

    /** 审核驳回：PENDING_REVIEW ➔ DRAFT，原因必填（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90） */
    public KnowledgeLifecycleResult reject(String articleId, String operatorId, String operatorRole, String reason) {
        KnowledgeVersion version = store.rejectToDraft(articleId, operatorId, operatorRole, reason);
        return new KnowledgeLifecycleResult(articleId, version.getVersionId(), KnowledgeStatus.DRAFT,
                NOT_REQUIRED, "已驳回并退回草稿，原因：" + reason);
    }

    /**
     * 下线：PUBLISHED ➔ OFFLINE，并同步 ES 切片状态
     * （AC-27 · specs/09-prd-spec-test-traceability.md:93：下线后搜索与 RAG 均不再返回）。
     *
     * <p>ES 同步失败不回滚知识下线事实，标记待补偿后可用 reindex/重新发布修复（RD-006/RD-008）。</p>
     */
    public KnowledgeLifecycleResult offline(String articleId, String operatorId, String operatorRole, String reason) {
        KnowledgeVersion version = store.offline(articleId, operatorId, operatorRole, reason);

        boolean esSynced = indexService.updateChunkStatusByArticleId(articleId, KnowledgeStatus.OFFLINE.getValue());
        String indexStatus = esSynced ? KnowledgeStatus.OFFLINE.getValue() + "_SYNCED" : PENDING_COMPENSATION;
        String message = esSynced
                ? "已下线，搜索与 RAG 索引均不再返回该版本"
                : "已下线，但 RAG 索引状态同步失败，已标记待补偿";
        return new KnowledgeLifecycleResult(articleId, version.getVersionId(), KnowledgeStatus.OFFLINE, indexStatus, message);
    }

    /**
     * 索引补偿重建：仅对已发布知识执行（RD-008 · specs/04-resilience-degradation.md:93）。
     *
     * <p>先把该文章现有切片置为 OFFLINE（不物理删除，AC-27 语义等价），再按当前版本重新切片入库，
     * 避免补偿后出现同一文章的新旧切片同时可见。</p>
     */
    public KnowledgeLifecycleResult reindex(String articleId) {
        KnowledgeArticle article = store.requireArticle(articleId);
        if (article.getStatus() != KnowledgeStatus.PUBLISHED) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "仅已发布(PUBLISHED)知识可重建索引，当前状态: " + article.getStatus());
        }
        KnowledgeVersion version = store.requireCurrentVersion(article);

        indexService.updateChunkStatusByArticleId(articleId, KnowledgeStatus.OFFLINE.getValue());
        ElasticsearchIndexService.IndexResult esResult = pipelineService.indexVersion(article, version, 0);
        String indexStatus = isIndexed(esResult) ? INDEXED : PENDING_COMPENSATION;
        return new KnowledgeLifecycleResult(articleId, version.getVersionId(), KnowledgeStatus.PUBLISHED,
                indexStatus, esResult.getMessage());
    }

    /**
     * 判断索引是否真正写入 ES。
     *
     * <p>ES 不可达时 indexChunks 会走本地快照降级并返回 success=true（供上传链路追踪用），
     * 但那不是索引成功；按 RD-013（specs/04-resilience-degradation.md:142，
     * 「禁止用空成功响应掩盖失败」）此处按 esStatus 复核。</p>
     */
    private boolean isIndexed(ElasticsearchIndexService.IndexResult esResult) {
        if (esResult == null || !esResult.isSuccess()) {
            return false;
        }
        Object esStatus = esResult.getDetails() == null ? null : esResult.getDetails().get("esStatus");
        return !"OFFLINE_FALLBACK".equals(String.valueOf(esStatus));
    }

    /**
     * 显式物理清理该文章的 ES 切片（管理用途）。
     *
     * <p>知识下线只做逻辑标记；已发布知识不物理删除，本方法仅在明确要求清理时调用，
     * 不进入任何业务链路（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515）。</p>
     */
    public long purgeEsChunks(String articleId) {
        store.requireArticle(articleId);
        return indexService.deleteChunksByArticleId(articleId);
    }

    /** 确保索引可用（管理端初始化，MR-011 · specs/10-model-rag-integration.md:151） */
    public boolean ensureIndexReady() {
        return indexService.ensureIndexReady();
    }

    /**
     * 存量切片 status 回填：严格状态过滤上线的前置动作，
     * 否则历史切片在检索中全部不可见（AI-001 只读 PUBLISHED · specs/02-ai-api-json-schema.md:14）。
     */
    public long backfillMissingStatus() {
        long updated = indexService.backfillMissingStatus();
        if (updated < 0) {
            throw new BizException(ErrorCode.SYSTEM_ERROR, "ES 不可用，存量切片状态回填失败");
        }
        return updated;
    }

    /** 供上层读取状态过滤常量，避免散落字面量 */
    public String publishedStatus() {
        return EsQueryDsl.STATUS_PUBLISHED;
    }
}
