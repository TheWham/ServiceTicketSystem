package com.itticket.rag.service;

import com.itticket.rag.dto.AiFeedbackCandidate;
import com.itticket.rag.entity.KnowledgeArticle;
import com.itticket.rag.entity.KnowledgeVersion;
import com.itticket.rag.enums.KnowledgeRiskLevel;
import com.itticket.rag.enums.KnowledgeStatus;
import com.itticket.rag.mapper.KnowledgeArticleMapper;
import com.itticket.rag.mapper.KnowledgeVersionMapper;
import com.itticket.rag.support.AiKnowledgeSanitizer;
import com.itticket.rag.support.KnowledgeContent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.HexFormat;

@Slf4j
@Service
@RequiredArgsConstructor
public class AiFeedbackKnowledgeService {
    private final KnowledgeArticleMapper articles;
    private final KnowledgeVersionMapper versions;
    private final KnowledgeStore store;

    /** 来源主键保证跨重启/跨节点幂等；文章、版本、审核记录及事件原子提交。 */
    @Transactional
    public boolean capture(AiFeedbackCandidate source) {
        String digest = digest(source.interactionId());
        String articleId = "ai-" + digest;
        if (articles.selectById(articleId) != null) return false;
        if (source.question() == null || source.question().isBlank()
                || source.answer() == null || source.answer().isBlank()
                || AiKnowledgeSanitizer.containsInjection(source.question() + "\n" + source.answer())) {
            log.warn("AI knowledge source skipped by content guard: interactionId={}", source.interactionId());
            return false;
        }
        String question = AiKnowledgeSanitizer.redact(source.question());
        String answer = AiKnowledgeSanitizer.redact(source.answer());
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        KnowledgeArticle article = new KnowledgeArticle();
        article.setArticleId(articleId);
        article.setStatus(KnowledgeStatus.DRAFT);
        article.setCategoryId(source.categoryId() == null || source.categoryId().isBlank() ? "C_OTH" : source.categoryId());
        article.setCurrentVersionId("av-" + digest);
        article.setRiskLevel("C_ACC".equals(source.categoryId()) ? KnowledgeRiskLevel.HIGH : KnowledgeRiskLevel.NORMAL);
        article.setVersion(0L);
        article.setCreatedAt(now);
        article.setUpdatedAt(now);
        articles.insert(article);

        KnowledgeVersion version = new KnowledgeVersion();
        version.setVersionId(article.getCurrentVersionId());
        version.setArticleId(articleId);
        version.setVersionNo(1);
        version.setContent(KnowledgeContent.build(truncate(question, 100), truncate(answer, 200),
                "AI客服 用户确认解决", "## 问题\n\n" + question + "\n\n## 解决方法\n\n" + answer));
        version.setAuthorId(source.authorId());
        version.setChangeNote("AI通用回答；员工反馈HELPFUL；session=" + source.sessionId()
                + "；interaction=" + source.interactionId());
        version.setCreatedAt(now);
        version.setUpdatedAt(now);
        versions.insert(version);
        store.submitForReview(articleId, source.authorId(), "SYSTEM", "AI客服有帮助反馈自动脱敏提审，需人工核实内容");
        return true;
    }

    private static String digest(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8))).substring(0, 60);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static String truncate(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }
}
