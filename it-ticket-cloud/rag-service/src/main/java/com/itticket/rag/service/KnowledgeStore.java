package com.itticket.rag.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeTransition;
import com.itticket.rag.entity.KnowledgeVersion;
import com.itticket.rag.entity.OutboxEvent;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import com.itticket.rag.mapper.KnowledgeTransitionMapper;
import com.itticket.rag.mapper.KnowledgeVersionMapper;
import com.itticket.rag.mapper.OutboxEventMapper;
import com.itticket.rag.support.Ids;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * ============================================================================
 * 知识状态机持久化层 (KnowledgeStore)
 * ============================================================================
 *
 * 【契约规范说明】（路径相对仓库根目录 docs/）：
 * 1. 每个迁移在事务内校验「当前状态 + 操作者角色 + 乐观锁版本」，不合法组合一律拒绝
 *    （SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90）。
 * 2. 合法迁移追加一条 knowledge_transition 审计记录，状态不可覆盖历史
 *    （SM-001 · specs/03-business-state-machine.md:12）。
 * 3. 状态先写主对象与流转记录，再写领域事实事件（SM-EVENT-001 · specs/03-business-state-machine.md:103；
 *    EV-001 信封 · specs/07-domain-events-outbox-redis.md:12）；
 *    索引等外部副作用由上层在事务外执行
 *    （RD-013 · specs/04-resilience-degradation.md:142：外部调用不得持有主事务数据库连接）。
 *
 * 【角色约定】网关透传的 X-User-Role：知识库管理员为 KNOWLEDGE_ADMIN（KB_ADMIN 为历史别名），
 * 平台管理员为 PLATFORM_ADMIN；比较统一大小写无关。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class KnowledgeStore {

    /** 状态迁移动作码 (DOMAIN_ACTION)，与 event_type 严格区分（SM-EVENT-001 · specs/03-business-state-machine.md:103） */
    public static final String ACTION_SUBMIT_REVIEW = "KNOWLEDGE_SUBMIT_REVIEW";
    public static final String ACTION_PUBLISH = "KNOWLEDGE_PUBLISH";
    public static final String ACTION_REJECT = "KNOWLEDGE_REJECT";
    public static final String ACTION_OFFLINE = "KNOWLEDGE_OFFLINE";

    /** 领域事实事件类型 (SCREAMING_SNAKE_CASE)，见 SM-EVENT-001 · specs/03-business-state-machine.md:103 */
    public static final String EVENT_SUBMITTED = "KNOWLEDGE_SUBMITTED";
    public static final String EVENT_PUBLISHED = "KNOWLEDGE_PUBLISHED";
    public static final String EVENT_OFFLINE = "KNOWLEDGE_OFFLINE";
    public static final String EVENT_INDEX_REFRESH = "KNOWLEDGE_INDEX_REFRESH_REQUESTED";

    /** 平台管理员角色码（高风险知识复核，PRD §16.4 · docs/IT服务工单系统PRD-Ultimate.md:515） */
    public static final String ROLE_PLATFORM_ADMIN = "PLATFORM_ADMIN";

    /** 平台复核结论 */
    private static final String PLATFORM_DECISION_APPROVED = "APPROVED";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final KnowledgeArticleMapper articleMapper;
    private final KnowledgeVersionMapper versionMapper;
    private final KnowledgeTransitionMapper transitionMapper;
    private final OutboxEventMapper outboxEventMapper;

    /** 读取知识文章，不存在直接拒绝 */
    public KnowledgeArticle requireArticle(String articleId) {
        if (articleId == null || articleId.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "知识 ID 不能为空");
        }
        KnowledgeArticle article = articleMapper.selectById(articleId);
        if (article == null) {
            throw new BizException(ErrorCode.PARAM_INVALID, "知识不存在: " + articleId);
        }
        return article;
    }

    /** 读取文章当前版本（草稿/待审/已发布均有当前版本指针） */
    public KnowledgeVersion requireCurrentVersion(KnowledgeArticle article) {
        String versionId = article.getCurrentVersionId();
        KnowledgeVersion version = versionId == null ? null : versionMapper.selectById(versionId);
        if (version == null) {
            throw new BizException(ErrorCode.SYSTEM_ERROR,
                    "知识缺少当前版本记录，无法执行流转: " + article.getArticleId());
        }
        return version;
    }

    /**
     * DRAFT ➔ PENDING_REVIEW（提交审核）。
     *
     * @param remark 提审备注，选填
     */
    @Transactional
    public KnowledgeVersion submitForReview(String articleId, String operatorId, String operatorRole, String remark) {
        KnowledgeArticle article = requireArticle(articleId);
        if (article.getStatus() != KnowledgeStatus.DRAFT) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "仅草稿(DRAFT)可提交审核，当前状态: " + article.getStatus());
        }
        KnowledgeVersion version = requireCurrentVersion(article);

        article.setStatus(KnowledgeStatus.PENDING_REVIEW);
        article.setUpdatedAt(LocalDateTime.now());
        updateArticle(article);

        insertTransition(articleId, version.getVersionId(), KnowledgeStatus.DRAFT, KnowledgeStatus.PENDING_REVIEW,
                ACTION_SUBMIT_REVIEW, operatorId, operatorRole, remark);

        ObjectNode payload = payload(articleId, version.getVersionId());
        payload.put("author_id", version.getAuthorId());
        insertEvent(EVENT_SUBMITTED, articleId, payload, article.getVersion());
        return version;
    }

    /**
     * PENDING_REVIEW ➔ PUBLISHED（审核通过并发布）。
     *
     * <p>守卫：作者不得自审（AC-25 · specs/09-prd-spec-test-traceability.md:91）；
     * 高风险知识须平台管理员复核（PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515；
     * SM-KNOWLEDGE-001 迁移表「审核通过」行）。</p>
     */
    @Transactional
    public KnowledgeVersion approveAndPublish(String articleId, String operatorId, String operatorRole, String changeNote) {
        KnowledgeArticle article = requireArticle(articleId);
        if (article.getStatus() != KnowledgeStatus.PENDING_REVIEW) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "仅待审核(PENDING_REVIEW)可发布，当前状态: " + article.getStatus());
        }
        KnowledgeVersion version = requireCurrentVersion(article);

        if (version.getAuthorId() != null && version.getAuthorId().equals(operatorId)) {
            throw new BizException(ErrorCode.FORBIDDEN, "作者不得审核自己提交的内容（AC-25）");
        }
        boolean highRisk = KnowledgeRiskLevel.normalize(article.getRiskLevel()).isHighRisk();
        if (highRisk && !ROLE_PLATFORM_ADMIN.equalsIgnoreCase(operatorRole)) {
            throw new BizException(ErrorCode.FORBIDDEN, "高风险知识须由平台管理员复核后发布（PRD §16.4）");
        }

        LocalDateTime now = LocalDateTime.now();
        version.setReviewerId(operatorId);
        version.setPublishedAt(now);
        if (highRisk) {
            // 高风险知识的平台管理员复核留痕（PRD §16.4）
            version.setPlatformReviewerId(operatorId);
            version.setPlatformReviewedAt(now);
            version.setPlatformReviewDecision(PLATFORM_DECISION_APPROVED);
        }
        if (changeNote != null && !changeNote.isBlank()) {
            // 远端 knowledge_version.change_note 为 varchar(255)
            version.setChangeNote(truncate(changeNote, 255));
        }
        versionMapper.updateById(version);

        article.setStatus(KnowledgeStatus.PUBLISHED);
        article.setCurrentVersionId(version.getVersionId());
        article.setUpdatedAt(now);
        updateArticle(article);

        insertTransition(articleId, version.getVersionId(), KnowledgeStatus.PENDING_REVIEW, KnowledgeStatus.PUBLISHED,
                ACTION_PUBLISH, operatorId, operatorRole, changeNote);

        // EV-001（specs/07-domain-events-outbox-redis.md:12）/ EV-008（:85）：
        // 同一聚合每个版本只允许一条事件（uk_aggregate_version 唯一约束）。
        // 发布事务只发 KNOWLEDGE_PUBLISHED；索引刷新由同步内联执行（见上层），
        // 不另发 KNOWLEDGE_INDEX_REFRESH_REQUESTED——该事件属于异步 IndexWorker 链路（下一轮）。
        insertEvent(EVENT_PUBLISHED, articleId, payload(articleId, version.getVersionId()), article.getVersion());
        return version;
    }

    /** PENDING_REVIEW ➔ DRAFT（审核驳回，必须给出原因） */
    @Transactional
    public KnowledgeVersion rejectToDraft(String articleId, String operatorId, String operatorRole, String reason) {
        KnowledgeArticle article = requireArticle(articleId);
        if (article.getStatus() != KnowledgeStatus.PENDING_REVIEW) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "仅待审核(PENDING_REVIEW)可驳回，当前状态: " + article.getStatus());
        }
        if (reason == null || reason.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "驳回必须填写原因（SM-KNOWLEDGE-001）");
        }
        KnowledgeVersion version = requireCurrentVersion(article);

        version.setReviewerId(operatorId);
        versionMapper.updateById(version);

        article.setStatus(KnowledgeStatus.DRAFT);
        article.setUpdatedAt(LocalDateTime.now());
        updateArticle(article);

        insertTransition(articleId, version.getVersionId(), KnowledgeStatus.PENDING_REVIEW, KnowledgeStatus.DRAFT,
                ACTION_REJECT, operatorId, operatorRole, reason);
        return version;
    }

    /** PUBLISHED ➔ OFFLINE（下线，必须给出原因） */
    @Transactional
    public KnowledgeVersion offline(String articleId, String operatorId, String operatorRole, String reason) {
        KnowledgeArticle article = requireArticle(articleId);
        if (article.getStatus() != KnowledgeStatus.PUBLISHED) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "仅已发布(PUBLISHED)知识可下线，当前状态: " + article.getStatus());
        }
        if (reason == null || reason.isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "下线必须填写原因（SM-KNOWLEDGE-001）");
        }
        KnowledgeVersion version = requireCurrentVersion(article);

        article.setStatus(KnowledgeStatus.OFFLINE);
        article.setUpdatedAt(LocalDateTime.now());
        updateArticle(article);

        insertTransition(articleId, version.getVersionId(), KnowledgeStatus.PUBLISHED, KnowledgeStatus.OFFLINE,
                ACTION_OFFLINE, operatorId, operatorRole, reason);
        insertEvent(EVENT_OFFLINE, articleId, payload(articleId, version.getVersionId()), article.getVersion());
        return version;
    }

    // ---------------------------------------------------------------- 内部

    /** 乐观锁更新：version 放入 WHERE 条件并递增，0 行表示并发冲突 */
    private void updateArticle(KnowledgeArticle article) {
        if (article.getVersion() == null) {
            article.setVersion(0L);
        }
        if (articleMapper.updateById(article) == 0) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "知识状态已被其他操作变更，请刷新后重试");
        }
    }

    private void insertTransition(String articleId, String versionId, KnowledgeStatus from, KnowledgeStatus to,
                                  String eventCode, String operatorId, String operatorRole, String reason) {
        KnowledgeTransition transition = new KnowledgeTransition();
        transition.setTransitionId(Ids.next("kt"));
        transition.setArticleId(articleId);
        transition.setVersionId(versionId);
        transition.setFromStatus(from.getValue());
        transition.setToStatus(to.getValue());
        transition.setEventCode(eventCode);
        transition.setOperatorId(operatorId);
        transition.setOperatorRole(operatorRole);
        // 远端 knowledge_transition.reason 由 V2_2 建为 varchar(255)
        transition.setReason(reason == null ? null : truncate(reason, 255));
        transition.setOccurredAt(LocalDateTime.now());
        transitionMapper.insert(transition);
    }

    private void insertEvent(String eventType, String articleId, ObjectNode payload) {
        insertEvent(eventType, articleId, payload, null);
    }

    /**
     * 写领域事实事件（EV-001 信封 · specs/07-domain-events-outbox-redis.md:12）。
     *
     * <p>聚合版本取文章的乐观锁版本，保证同一聚合上的事件单调递增
     * （EV-008 · specs/07-domain-events-outbox-redis.md:85）。
     * 在 {@link #updateArticle} 乐观锁更新之后调用时，文章的 version 已是迁移后的新值。</p>
     */
    private void insertEvent(String eventType, String articleId, ObjectNode payload, Long aggregateVersion) {
        LocalDateTime now = LocalDateTime.now();
        OutboxEvent event = new OutboxEvent();
        event.setEventId(Ids.next("ev"));
        event.setEventType(eventType);
        event.setAggregateType("KNOWLEDGE");
        event.setAggregateId(articleId);
        event.setEventVersion(1);
        event.setAggregateVersion(aggregateVersion == null ? 0L : aggregateVersion);
        event.setPayloadJson(truncate(payload.toString(), 1000));
        event.setStatus("PENDING");
        event.setAttempts(0);
        event.setNextAttemptAt(now);
        event.setCreatedAt(now);
        event.setUpdatedAt(now);
        outboxEventMapper.insert(event);
    }

    /** 事件最小载荷（EV-008 · specs/07-domain-events-outbox-redis.md:85：字段名 snake_case，禁止空对象） */
    private ObjectNode payload(String articleId, String versionId) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("article_id", articleId);
        if (versionId != null) {
            node.put("version_id", versionId);
        }
        return node;
    }

    private static String truncate(String value, int maxLength) {
        if (value == null) {
            return null;
        }
        return value.length() <= maxLength ? value : value.substring(0, maxLength);
    }
}
