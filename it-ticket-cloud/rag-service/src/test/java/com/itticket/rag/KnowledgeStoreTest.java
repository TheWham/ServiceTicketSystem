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
        version.setContentJson(KnowledgeContent.build("网络排查指南", "摘要", null, "正文"));
        version.setAuthorId(AUTHOR);
        Mockito.when(versionMapper.selectById("ver-1")).thenReturn(version);
        return article;
    }

    private void stubUpdateOk() {
        Mockito.when(articleMapper.updateById(Mockito.any(KnowledgeArticle.class))).thenReturn(1);
    }

    @Test
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

    @Test
    public void submitIsRejectedWhenNotDraft() {
        stubArticle(KnowledgeStatus.PUBLISHED, KnowledgeRiskLevel.NORMAL);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.submitForReview("art-1", AUTHOR, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.ILLEGAL_TRANSITION.getCode(), ex.getErrorCode().getCode());
        Mockito.verify(transitionMapper, Mockito.never()).insert(Mockito.any(KnowledgeTransition.class));
    }

    @Test
    public void publishIsRejectedWhenReviewerIsTheAuthor() {
        stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.NORMAL);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.approveAndPublish("art-1", AUTHOR, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.FORBIDDEN.getCode(), ex.getErrorCode().getCode(),
                "AC-25：作者不得审核自己提交的内容");
        Mockito.verify(articleMapper, Mockito.never()).updateById(Mockito.any(KnowledgeArticle.class));
    }

    @Test
    public void highRiskPublishRequiresPlatformAdmin() {
        stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.HIGH);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.approveAndPublish("art-1", REVIEWER, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.FORBIDDEN.getCode(), ex.getErrorCode().getCode());
    }

    @Test
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

        Assertions.assertEquals(List.of(KnowledgeStore.EVENT_PUBLISHED, KnowledgeStore.EVENT_INDEX_REFRESH),
                captureEventTypes());
    }

    @Test
    public void concurrentModificationFailsTheTransition() {
        stubArticle(KnowledgeStatus.PENDING_REVIEW, KnowledgeRiskLevel.NORMAL);
        Mockito.when(articleMapper.updateById(Mockito.any(KnowledgeArticle.class))).thenReturn(0);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.approveAndPublish("art-1", REVIEWER, "KNOWLEDGE_ADMIN", null));

        Assertions.assertEquals(ErrorCode.ILLEGAL_TRANSITION.getCode(), ex.getErrorCode().getCode());
        Mockito.verify(outboxEventMapper, Mockito.never()).insert(Mockito.any(OutboxEvent.class));
    }

    @Test
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

    @Test
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

    @Test
    public void offlineIsRejectedWhenNotPublished() {
        stubArticle(KnowledgeStatus.DRAFT, KnowledgeRiskLevel.NORMAL);

        BizException ex = Assertions.assertThrows(BizException.class,
                () -> store.offline("art-1", REVIEWER, "KNOWLEDGE_ADMIN", "内容已过期"));

        Assertions.assertEquals(ErrorCode.ILLEGAL_TRANSITION.getCode(), ex.getErrorCode().getCode());
    }

    @Test
    public void missingArticleIsRejected() {
        Mockito.when(articleMapper.selectById("art-x")).thenReturn(null);

        Assertions.assertThrows(BizException.class,
                () -> store.submitForReview("art-x", AUTHOR, "KNOWLEDGE_ADMIN", null));
    }

    private KnowledgeTransition captureTransition() {
        ArgumentCaptor<KnowledgeTransition> captor = ArgumentCaptor.forClass(KnowledgeTransition.class);
        Mockito.verify(transitionMapper).insert(captor.capture());
        return captor.getValue();
    }

    private List<String> captureEventTypes() {
        ArgumentCaptor<OutboxEvent> captor = ArgumentCaptor.forClass(OutboxEvent.class);
        Mockito.verify(outboxEventMapper, Mockito.atLeastOnce()).insert(captor.capture());
        return captor.getAllValues().stream().map(OutboxEvent::getEventType).toList();
    }
}
