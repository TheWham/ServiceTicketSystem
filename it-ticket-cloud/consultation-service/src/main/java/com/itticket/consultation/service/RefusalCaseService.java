package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.api.PagedData;
import com.itticket.consultation.dto.BadCaseReviewView;
import com.itticket.consultation.dto.MessageProjection;
import com.itticket.consultation.dto.RefusalCaseDetail;
import com.itticket.consultation.dto.RefusalCaseItem;
import com.itticket.consultation.dto.RefusalCaseRow;
import com.itticket.consultation.dto.ReviewRequest;
import com.itticket.consultation.entity.BadCaseReview;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.entity.GoldenCase;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.mapper.BadCaseReviewMapper;
import com.itticket.consultation.mapper.ConsultationMessageMapper;
import com.itticket.consultation.mapper.GoldenCaseMapper;
import com.itticket.consultation.mapper.RefusalCaseMapper;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * 拒答案例查询与处置(管理端)。
 *
 * <p>待处置列表实时联查 consultation_message(AI REFUSE 消息),不建同步队列;
 * 处置写 bad_case_review(GOLDEN_* 同时写 golden_case,同库单数据源同事务)。
 * UNIQUE(ai_message_id) 保证一条拒答只处置一次,重复返回 409。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RefusalCaseService {

    private static final Set<String> DECISIONS = Set.of("GOLDEN_QA", "GOLDEN_REFUSAL", "DISCARD");
    private static final Set<String> STATUS_FILTERS = Set.of("PENDING", "REVIEWED", "ALL");
    /** 对抗样本缺省期望答案:回归时验证"仍然拒答"。 */
    private static final String DEFAULT_REFUSAL_ANSWER =
            "系统应给出确定性拒答并引导转人工/提单,不得编造答案。";

    private final RefusalCaseMapper refusalCaseMapper;
    private final BadCaseReviewMapper badCaseReviewMapper;
    private final GoldenCaseMapper goldenCaseMapper;
    private final ConsultationMessageMapper messageMapper;

    public PagedData<RefusalCaseItem> page(int page, int pageSize, String status, String keyword) {
        String statusFilter = normalizeStatus(status);
        String keywordFilter = (keyword == null || keyword.isBlank()) ? null : keyword.trim();
        Page<RefusalCaseRow> result = refusalCaseMapper.selectRefusalCases(
                new Page<>(Math.max(1, page), Math.min(Math.max(1, pageSize), 100)),
                statusFilter, keywordFilter);
        List<RefusalCaseItem> items = new ArrayList<>();
        for (RefusalCaseRow row : result.getRecords()) {
            items.add(new RefusalCaseItem(row.getMessageId(), row.getSessionId(), row.getQuestionText(),
                    row.getRefusalReason(), row.getConfidence(), row.getSentAt(),
                    row.getReviewStatus(), row.getDecision()));
        }
        return new PagedData<>(items, Math.max(1, page), Math.min(Math.max(1, pageSize), 100), result.getTotal());
    }

    public RefusalCaseDetail detail(String messageId) {
        ConsultationMessage aiMsg = requireRefuseMessage(messageId);
        String question = latestEmployeeQuestion(aiMsg.getSessionId(), aiMsg.getSentAt());
        RefusalCaseItem item = toItem(aiMsg, question, currentReview(messageId));
        List<MessageProjection> context = messageMapper.selectList(
                        new LambdaQueryWrapper<ConsultationMessage>()
                                .eq(ConsultationMessage::getSessionId, aiMsg.getSessionId())
                                .orderByAsc(ConsultationMessage::getSentAt)
                                .last("LIMIT 20"))
                .stream().map(MessageProjection::of).toList();
        return new RefusalCaseDetail(item, context);
    }

    @Transactional
    public BadCaseReviewView review(String messageId, ReviewRequest request, CurrentUser user) {
        requireManageRole(user);
        String decision = request.decision() == null ? "" : request.decision().trim().toUpperCase(Locale.ROOT);
        if (!DECISIONS.contains(decision)) {
            throw ApiException.validation(List.of(com.itticket.consultation.api.FieldIssue.invalid("decision", "decision 必须是 GOLDEN_QA / GOLDEN_REFUSAL / DISCARD")));
        }
        ConsultationMessage aiMsg = requireRefuseMessage(messageId);
        if (badCaseReviewMapper.selectCount(new LambdaQueryWrapper<BadCaseReview>()
                .eq(BadCaseReview::getAiMessageId, messageId)) > 0) {
            throw new ApiException(ApiCode.IDEMPOTENCY_CONFLICT, "该拒答案例已被处置,不可重复提交");
        }
        String question = latestEmployeeQuestion(aiMsg.getSessionId(), aiMsg.getSentAt());
        String interactionId = extractMetadata(aiMsg, "interactionId");

        BadCaseReview review = new BadCaseReview();
        review.setAiMessageId(messageId);
        review.setSessionId(aiMsg.getSessionId());
        review.setInteractionId(interactionId);
        review.setQuestionText(question == null ? "" : question);
        review.setRefusalReason(extractMetadata(aiMsg, "refusalReason"));
        review.setDecision(decision);
        review.setReviewNote(request.reviewNote());
        review.setReviewedBy(user.userId());
        review.setReviewedAt(Times.nowUtc());

        Long goldenCaseId = null;
        if ("GOLDEN_QA".equals(decision) || "GOLDEN_REFUSAL".equals(decision)) {
            goldenCaseId = insertGoldenCase(messageId, decision, request, question, user.userId());
        }
        review.setGoldenCaseId(goldenCaseId);
        try {
            badCaseReviewMapper.insert(review);
        } catch (DuplicateKeyException e) {
            throw new ApiException(ApiCode.IDEMPOTENCY_CONFLICT, "该拒答案例已被处置,不可重复提交");
        }
        log.info("[refusal-case] 处置完成 messageId={} decision={} goldenCaseId={} operator={}",
                messageId, decision, goldenCaseId, user.userId());
        return toView(review);
    }

    // ---------------------------------------------------------------- 内部

    private Long insertGoldenCase(String messageId, String decision, ReviewRequest request,
                                  String question, String operatorId) {
        boolean adversarial = "GOLDEN_REFUSAL".equals(decision);
        String query = (request.goldenQuery() == null || request.goldenQuery().isBlank())
                ? (question == null ? "" : question) : request.goldenQuery().trim();
        String answer = (request.goldenAnswer() == null || request.goldenAnswer().isBlank())
                ? (adversarial ? DEFAULT_REFUSAL_ANSWER : null) : request.goldenAnswer().trim();
        if (query.isBlank()) {
            throw ApiException.validation(List.of(com.itticket.consultation.api.FieldIssue.required("goldenQuery", "会话中未找到员工提问原文,请手动填写 goldenQuery")));
        }
        if (answer == null || answer.isBlank()) {
            throw ApiException.validation(List.of(com.itticket.consultation.api.FieldIssue.required("goldenAnswer", "GOLDEN_QA 必须填写标准答案(补知识后可回答的期望答案)")));
        }
        GoldenCase goldenCase = new GoldenCase();
        goldenCase.setNaturalKey("BC-" + messageId);
        goldenCase.setCategory((request.category() == null || request.category().isBlank())
                ? (adversarial ? "越界拒答" : "知识缺口补录") : request.category().trim());
        goldenCase.setDifficulty((request.difficulty() == null || request.difficulty().isBlank())
                ? "HARD" : request.difficulty().trim());
        goldenCase.setQuery(query);
        goldenCase.setGroundTruthAnswer(answer);
        goldenCase.setExpectedKeywordsJson(toKeywordsJson(request.expectedKeywords(),
                adversarial ? List.of("转人工") : List.of()));
        goldenCase.setIsConflictCheck(0);
        goldenCase.setIsAdversarial(adversarial ? 1 : 0);
        goldenCase.setSourceType("BAD_CASE");
        goldenCase.setSourceAiMessageId(messageId);
        goldenCase.setEnabled(1);
        goldenCase.setCreatedBy(operatorId);
        goldenCase.setCreatedAt(Times.nowUtc());
        goldenCaseMapper.insert(goldenCase);
        return goldenCase.getId();
    }

    private ConsultationMessage requireRefuseMessage(String messageId) {
        ConsultationMessage aiMsg = messageMapper.selectById(messageId);
        if (aiMsg == null || aiMsg.getSenderType() != MessageSenderType.AI) {
            throw ApiException.notFound();
        }
        if (!"REFUSE".equals(extractMetadata(aiMsg, "replyType"))) {
            throw ApiException.validation(List.of(com.itticket.consultation.api.FieldIssue.invalid("messageId", "该 AI 消息不是拒答回复,不可进入处置流程")));
        }
        return aiMsg;
    }

    private String latestEmployeeQuestion(String sessionId, java.time.LocalDateTime before) {
        ConsultationMessage q = messageMapper.selectOne(new LambdaQueryWrapper<ConsultationMessage>()
                .eq(ConsultationMessage::getSessionId, sessionId)
                .eq(ConsultationMessage::getSenderType, MessageSenderType.EMPLOYEE)
                .lt(ConsultationMessage::getSentAt, before)
                .orderByDesc(ConsultationMessage::getSentAt)
                .last("LIMIT 1"));
        return q == null ? null : q.getContent();
    }

    private BadCaseReview currentReview(String messageId) {
        return badCaseReviewMapper.selectOne(new LambdaQueryWrapper<BadCaseReview>()
                .eq(BadCaseReview::getAiMessageId, messageId)
                .last("LIMIT 1"));
    }

    private RefusalCaseItem toItem(ConsultationMessage aiMsg, String question, BadCaseReview review) {
        return new RefusalCaseItem(aiMsg.getMessageId(), aiMsg.getSessionId(), question,
                extractMetadata(aiMsg, "refusalReason"), null, aiMsg.getSentAt(),
                review == null ? "PENDING" : "REVIEWED", review == null ? null : review.getDecision());
    }

    private BadCaseReviewView toView(BadCaseReview review) {
        return new BadCaseReviewView(review.getId(), review.getAiMessageId(), review.getSessionId(),
                review.getQuestionText(), review.getRefusalReason(), review.getDecision(),
                review.getGoldenCaseId(), review.getReviewNote(), review.getReviewedBy(), review.getReviewedAt());
    }

    private String extractMetadata(ConsultationMessage aiMsg, String field) {
        if (aiMsg.getCitationJson() == null || aiMsg.getCitationJson().isBlank()) {
            return null;
        }
        try {
            Map<String, Object> metadata = Json.readMap(aiMsg.getCitationJson());
            Object value = metadata == null ? null : metadata.get(field);
            return value == null ? null : String.valueOf(value);
        } catch (Exception e) {
            log.warn("[refusal-case] citation_json 解析失败 messageId={}", aiMsg.getMessageId());
            return null;
        }
    }

    private String toKeywordsJson(String raw, List<String> defaults) {
        List<String> keywords = new ArrayList<>();
        if (raw != null && !raw.isBlank()) {
            for (String k : raw.split("[,;,]")) {
                if (!k.isBlank()) keywords.add(k.trim());
            }
        }
        if (keywords.isEmpty()) keywords = defaults;
        return Json.write(keywords);
    }

    private void requireManageRole(CurrentUser user) {
        if (user.role() != com.itticket.consultation.enums.RoleCode.KNOWLEDGE_ADMIN
                && user.role() != com.itticket.consultation.enums.RoleCode.PLATFORM_ADMIN) {
            throw new ApiException(ApiCode.FORBIDDEN, "需要 知识库管理员 或 平台管理员 权限");
        }
    }

    private String normalizeStatus(String status) {
        String s = (status == null || status.isBlank()) ? "PENDING" : status.trim().toUpperCase(Locale.ROOT);
        if (!STATUS_FILTERS.contains(s)) {
            throw ApiException.validation(List.of(com.itticket.consultation.api.FieldIssue.invalid("status", "status 必须是 PENDING / REVIEWED / ALL")));
        }
        return s;
    }
}
