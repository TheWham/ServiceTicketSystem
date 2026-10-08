package com.itticket.rag;

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
import com.itticket.rag.service.KnowledgeStore;
import com.itticket.rag.support.KnowledgeContent;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mockito;

import java.util.List;

/**
 * 知识状态机守卫测试（SM-KNOWLEDGE-001 / SM-001 / AC-25 / PRD §16.4）。
 *
 * <p>规范引用（路径相对仓库根目录 docs/）：</p>
 * <ul>
 *   <li>SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90 —— 四条迁移边与角色守卫；</li>
 *   <li>SM-001 · specs/03-business-state-machine.md:12 —— 每次迁移写一条流转审计；</li>
 *   <li>AC-25 · specs/09-prd-spec-test-traceability.md:91 —— 作者不得自审（publishIsRejectedWhenReviewerIsTheAuthor）；</li>
 *   <li>PRD §16.4 · IT服务工单系统PRD-Ultimate.md:515 —— 高风险须平台管理员复核（highRiskPublish*）；</li>
 *   <li>EV-008 · specs/07-domain-events-outbox-redis.md:85 —— 同一聚合版本只允许一条事件
 *       （highRiskPublishByPlatformAdminRecordsRecheckAndEmitsEvents 断言发布只发一条）。</li>
 * </ul>
 *
 * <p>纯单元测试：Mockito 打桩 mapper，不依赖数据库与 Spring 容器。</p>
 * 被测对象 KnowledgeStore 是知识库生命周期的唯一写入口，负责：
 *   DRAFT --submit--> PENDING_REVIEW --publish--> PUBLISHED --offline--> OFFLINE
 *   PENDING_REVIEW --reject--> DRAFT
 * 每次合法迁移必须同时完成三件事，缺一不可：
 *   1) 更新 knowledge_article 状态（乐观锁：updateById 影响 0 行即并发冲突，迁移作废）；
 *   2) 写 knowledge_transition 流转审计（event_code / from / to / 操作人 / 原因）；
 *   3) 写 outbox_event（EV-001 事件信封，异步驱动 ES 索引刷新，
 *      同一聚合版本受 uk_aggregate_version 唯一约束只允许一条）。
 * 三条安全红线（违反即 BizException）：
 *   - AC-25：作者不得审核自己提交的内容；
 *   - 高风险（HIGH_RISK）知识发布须 PLATFORM_ADMIN 复核并留痕；
 *   - reject / offline 必须给出原因（审计强制）。
 */
public class KnowledgeStoreTest {

    private final KnowledgeArticleMapper articleMapper = Mockito.mock(KnowledgeArticleMapper.class);
    private final KnowledgeVersionMapper versionMapper = Mockito.mock(KnowledgeVersionMapper.class);
    private final KnowledgeTransitionMapper transitionMapper = Mockito.mock(KnowledgeTransitionMapper.class);
    private final OutboxEventMapper outboxEventMapper = Mockito.mock(OutboxEventMapper.class);

    private final KnowledgeStore store =
            new KnowledgeStore(articleMapper, versionMapper, transitionMapper, outboxEventMapper);

    private static final String AUTHOR = "kb_admin";
    private static final String REVIEWER = "U_ADM01";

    /**
     * 造一对“文章 + 当前版本”的桩数据：art-1 / ver-1，作者固定为 AUTHOR(kb_admin)。
     * 各用例用 status / riskLevel 两个维度摆出自己想要的初始局面，后续断言都以这对 ID 为锚点。
     */
    private KnowledgeArticle stubArticle(KnowledgeStatus status, KnowledgeRiskLevel riskLevel) {
        KnowledgeArticle article = new KnowledgeArticle();
        article.setArticleId("art-1");
        article.setStatus(status);
        article.setCurrentVersionId("ver-1");
        article.setCategoryId("C_NET");
        article.setRiskLevel(riskLevel);
        article.setVersion(0L);
        Mockito.when(articleMapper.selectById("art-1")).thenReturn(article);

        KnowledgeVersion version = new KnowledgeVersion();
        version.setVersionId("ver-1");
        version.setArticleId("art-1");
        version.setVersionNo(1);
        version.setContent(KnowledgeContent.build("网络排查指南", "摘要", null, "正文"));
        version.setAuthorId(AUTHOR);
        Mockito.when(versionMapper.selectById("ver-1")).thenReturn(version);
        return article;
    }

    /**
     * 约定乐观锁更新成功（updateById 返回 1 行）；
     * 不调用本桩的用例由 Mockito 默认返回 0，可自然覆盖“并发冲突导致迁移中止”的分支。
     */
    private void stubUpdateOk() {
        Mockito.when(articleMapper.updateById(Mockito.any(KnowledgeArticle.class))).thenReturn(1);
    }

    /** DRAFT ➔ PENDING_REVIEW：迁移成功并写一条流转审计 + KNOWLEDGE_SUBMITTED 事件（SM-KNOWLEDGE-001 · specs/03:90）     *
     * 提审主路径：DRAFT -> PENDING_REVIEW。
     * 断言三件事同时成立：文章状态已更新；流转审计 event/from/to/备注正确；
     * outbox 恰好发出一条 SUBMITTED 事件（驱动后续异步流程）。
     */
    public void submitMovesDraftToPendingReviewAndWritesAudit() {
        KnowledgeArticle article = stubArticle(KnowledgeStatus.DRAFT, KnowledgeRiskLevel.NORMAL);
        stubUpdateOk();

        store.submitForReview("art-1", AUTHOR, "KNOWLEDGE_ADMIN", "提审备注");

        Assertions.assertEquals(KnowledgeStatus.PENDING_REVIEW, article.getStatus());
        KnowledgeTransition transition = captureTransition();
        Assertions.assertEquals(KnowledgeStore.ACTION_SUBMIT_REVIEW, transition.getEventCode());
        Assertions.assertEquals("DRAFT", transition.getFromStatus());
        Assertions.assertEquals("PENDING_REVIEW", transition.getToStatus());
        Assertions.assertEquals("提审备注", transition.getReason());

        List<String> events = captureEventTypes();
        Assertions.assertEquals(List.of(KnowledgeStore.EVENT_SUBMITTED), events);
    }

    /** 非 DRAFT 状态提审一律拒绝，且不写审计（SM-KNOWLEDGE-001 迁移边白名单 · specs/03:90）     *
     * 守卫：非 DRAFT 状态（此处以 PUBLISHED 代表）不允许提审。
     * SM-001 原则——状态机未列出的组合一律拒绝，报 ILLEGAL_TRANSITION；
     * 并验证没有任何审计记录被写入（失败的操作不能留下“半条痕迹”）。
     */
    public void submitIsRejectedWhenNotDraft() {
        stubArticle(KnowledgeStatus.PUBLISHED, KnowledgeRiskLevel.NORMAL);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.submitForReview("art-1", AUTHOR, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.ILLEGAL_TRANSITION.getCode(), ex.getErrorCode().getCode());
        Mockito.verify(transitionMapper, Mockito.never()).insert(Mockito.any(KnowledgeTransition.class));
    }

    /** AC-25（specs/09:91）：作者本人发布被拒，且不产生任何状态写入     *
     * AC-25 安全红线：作者不得审核自己提交的内容。
     * stubArticle 固定作者为 AUTHOR，这里以同一人尝试 approveAndPublish，必须 FORBIDDEN，
     * 且文章状态不得被修改（若作者能自审，知识库审核机制形同虚设）。
     */
    public void publishIsRejectedWhenReviewerIsTheAuthor() {
        stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.NORMAL);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.approveAndPublish("art-1", AUTHOR, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.FORBIDDEN.getCode(), ex.getErrorCode().getCode(),
                "AC-25：作者不得审核自己提交的内容");
        Mockito.verify(articleMapper, Mockito.never()).updateById(Mockito.any(KnowledgeArticle.class));
    }

    /** PRD §16.4（PRD:515）：高风险知识由普通知识库管理员发布被拒     *
     * 高风险知识升级审核：risk_level=HIGH 的待审内容，普通 KNOWLEDGE_ADMIN 无权发布，
     * 必须 PLATFORM_ADMIN 复核（提权双人复核，防止高危操作指南绕过管控上线）。
     */
    public void highRiskPublishRequiresPlatformAdmin() {
        stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.HIGH);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.approveAndPublish("art-1", REVIEWER, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.FORBIDDEN.getCode(), ex.getErrorCode().getCode());
    }

    /** PRD §16.4：平台管理员发布高风险知识须留复核痕迹；EV-008（specs/07:85）：发布只发一条事件     *
     * 高风险发布全链路留痕：PLATFORM_ADMIN 复核通过时，
     * 除常规的 reviewer/published_at 外，还必须记录 platformReviewerId / platformReviewedAt /
     * platformReviewDecision=APPROVED（事后审计要能回答“谁批准了这条高危内容”）；
     * outbox 中 PUBLISHED 事件有且仅有一条（聚合版本唯一约束），索引刷新走异步链路。
     */
    public void highRiskPublishByPlatformAdminRecordsRecheckAndEmitsEvents() {
        KnowledgeArticle article = stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.HIGH);
        stubUpdateOk();

        KnowledgeVersion version = store.approveAndPublish("art-1", REVIEWER, "PLATFORM_ADMIN", "复核通过");

        Assertions.assertEquals(KnowledgeStatus.PUBLISHED, article.getStatus());
        Assertions.assertEquals(REVIEWER, version.getReviewerId());
        Assertions.assertEquals(REVIEWER, version.getPlatformReviewerId(), "高风险须记录平台管理员复核人");
        Assertions.assertNotNull(version.getPlatformReviewedAt());
        Assertions.assertEquals("APPROVED", version.getPlatformReviewDecision());
        Assertions.assertNotNull(version.getPublishedAt());

        KnowledgeTransition transition = captureTransition();
        Assertions.assertEquals(KnowledgeStore.ACTION_PUBLISH, transition.getEventCode());
        Assertions.assertEquals("PENDING_REVIEW", transition.getFromStatus());
        Assertions.assertEquals("PUBLISHED", transition.getToStatus());

        // 同一聚合版本只允许一条事件（uk_aggregate_version 唯一约束），索引刷新为异步链路事件，本轮不随发布同步发
        Assertions.assertEquals(List.of(KnowledgeStore.EVENT_PUBLISHED), captureEventTypes());
    }

    /** 乐观锁并发冲突（updateById 返回 0 行）时迁移失败且不发事件（SM-001 · specs/03:12）     *
     * 乐观锁防并发：updateById 返回 0 行表示“读到的版本已被别人改过”，
     * 迁移必须整体作废（ILLEGAL_TRANSITION），且不得发出任何 outbox 事件，
     * 避免 ES 索引被一次并未发生的状态变更误刷新。
     */
    public void concurrentModificationFailsTheTransition() {
        stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.NORMAL);
        Mockito.when(articleMapper.updateById(Mockito.any(KnowledgeArticle.class))).thenReturn(0);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.approveAndPublish("art-1", REVIEWER, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.ILLEGAL_TRANSITION.getCode(), ex.getErrorCode().getCode());
        Mockito.verify(outboxEventMapper, Mockito.never()).insert(Mockito.any(OutboxEvent.class));
    }

    /** 驳回必须带原因；合法驳回回 DRAFT 且原因写入流转审计（SM-KNOWLEDGE-001 · specs/03:90）     *
     * 驳回契约：reason 必填（纯空白同样拒绝），通过则回到 DRAFT；
     * 驳回原因不写 knowledge_version（该表无此列），落流转审计 transition.reason。
     */
    public void rejectRequiresReasonAndReturnsToDraft() {
        KnowledgeArticle article = stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.NORMAL);
        stubUpdateOk();

        Assertions.assertThrows(BizException.class,
                () -> store.rejectToDraft("art-1", REVIEWER, "KNOWLEDGE_ADMIN", "   "));

        KnowledgeVersion version = store.rejectToDraft("art-1", REVIEWER, "KNOWLEDGE_ADMIN", "解决步骤不完整");

        Assertions.assertEquals(KnowledgeStatus.DRAFT, article.getStatus());
        // 驳回原因写入流转审计（knowledge_version 没有 reject_reason 列）
        KnowledgeTransition transition = captureTransition();
        Assertions.assertEquals(KnowledgeStore.ACTION_REJECT, transition.getEventCode());
        Assertions.assertEquals("解决步骤不完整", transition.getReason());
        Assertions.assertEquals(REVIEWER, version.getReviewerId());
    }

    /** 下线必须带原因，成功下线写 KNOWLEDGE_OFFLINE 事件（SM-KNOWLEDGE-001 · specs/03:90）     *
     * 下线契约：reason 必填；PUBLISHED -> OFFLINE 成功后发 OFFLINE 事件，
     * 让异步链路把该知识从 ES 检索中摘除（下线知识绝不允许再被 AI 引用）。
     */
    public void offlineRequiresReasonAndEmitsOfflineEvent() {
        KnowledgeArticle article = stubArticle(KnowledgeStatus.PUBLISHED, KnowledgeRiskLevel.NORMAL);
        stubUpdateOk();

        Assertions.assertThrows(BizException.class,
                () -> store.offline("art-1", REVIEWER, "KNOWLEDGE_ADMIN", null));

        store.offline("art-1", REVIEWER, "KNOWLEDGE_ADMIN", "内容已过期");

        Assertions.assertEquals(KnowledgeStatus.OFFLINE, article.getStatus());
        KnowledgeTransition transition = captureTransition();
        Assertions.assertEquals(KnowledgeStore.ACTION_OFFLINE, transition.getEventCode());
        Assertions.assertEquals("内容已过期", transition.getReason());
        Assertions.assertEquals(List.of(KnowledgeStore.EVENT_OFFLINE), captureEventTypes());
    }

    /** 非 PUBLISHED 状态下线被拒（SM-KNOWLEDGE-001 迁移边白名单 · specs/03:90）     *
     * 守卫：只有 PUBLISHED 才能下线；DRAFT 调 offline 属状态机未列组合，一律 ILLEGAL_TRANSITION。
     */
    public void offlineIsRejectedWhenNotPublished() {
        stubArticle(KnowledgeStatus.DRAFT, KnowledgeRiskLevel.NORMAL);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.offline("art-1", REVIEWER, "KNOWLEDGE_ADMIN", "内容已过期"));

        Assertions.assertEquals(ErrorCode.ILLEGAL_TRANSITION.getCode(), ex.getErrorCode().getCode());
    }

    /** 文章不存在直接拒绝，不产生任何写入     *
     * 脏数据兜底：article_id 不存在（查询返回 null）按 BizException 拒绝，
     * 不允许抛出 NPE 之类的未受控异常。
     */
    public void missingArticleIsRejected() {
        Mockito.when(articleMapper.selectById("art-x")).thenReturn(null);

        Assertions.assertThrows(BizException.class,
                () -> store.submitForReview("art-x", AUTHOR, "KNOWLEDGE_ADMIN", null));
    }

    /**
     * 捕获本次迁移写入的流转审计记录（每次迁移恰好 insert 一次 transition）。
     */
    private KnowledgeTransition captureTransition() {
        ArgumentCaptor<KnowledgeTransition> captor = ArgumentCaptor.forClass(KnowledgeTransition.class);
        Mockito.verify(transitionMapper).insert(captor.capture());
        return captor.getValue();
    }

    /**
     * 收集本轮写入 outbox_event 的全部事件类型，按序返回。
     * 用于断言“一次迁移发出且只发出预期的事件集合”（uk_aggregate_version 约束下不允许重复发）。
     */
    private List<String> captureEventTypes() {
        ArgumentCaptor<OutboxEvent> captor = ArgumentCaptor.forClass(OutboxEvent.class);
        Mockito.verify(outboxEventMapper, Mockito.atLeastOnce()).insert(captor.capture());
        return captor.getAllValues().stream().map(OutboxEvent::getEventType).toList();
    }
}
