package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.itticket.consultation.adapter.GuardedRagClient;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.adapter.RagCaller;
import com.itticket.consultation.adapter.RagResult;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.api.RequestContext;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.AiChatRequest;
import com.itticket.consultation.dto.AiChatResponse;
import com.itticket.consultation.dto.AiFeedbackRequest;
import com.itticket.consultation.dto.AiFeedbackResponse;
import com.itticket.consultation.entity.AiInteraction;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.enums.AiReplyType;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.mapper.AiInteractionMapper;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 智能客服(AI-API-002 发送消息 / AI-API-003 反馈)。
 *
 * <p>能力边界(AI-001):只读当前 PUBLISHED 知识;可解释知识、追问或拒答;
 * 不执行命令、不调用业务系统、不创建或修改工单;转人工与提单入口始终可用。
 *
 * <p>失败语义:模型或检索故障一律降级为结构化拒答并置 {@code suggestTransfer=true},
 * 而不是抛 AI_UNAVAILABLE 错误。理由是 RD-006 允许二选一,而结构化拒答能让会话保持可用、
 * 对话记录完整,并且客户端拿到的永远是同一种结构(RD-013 要求降级结果可判定)。
 * 降级分类仍然写入日志与 {@code ai_interaction},便于按 RD-010 统计拒答率。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AiConsultationService {

    private static final String OP_CHAT = "AI_CHAT";
    private static final String OP_FEEDBACK = "AI_FEEDBACK";

    /**
     * 拒答时写入会话记录的固定话术。
     * 它不是模型生成内容,也不会出现在 {@code AiChatResponse.answerText}
     * (AI-004.3 约束 REFUSE 的 answerText 长度为 0),只用于让聊天记录可读。
     */
    private static final String REFUSAL_TRANSCRIPT =
            "暂时无法给出可靠的办公 IT 建议，请转人工或直接提交工单。";

    private final ConsultationTransitionService transitionService;
    private final ConsultationMessageService messageService;
    private final KnowledgeQueryService knowledgeQueryService;
    private final GuardedRagClient ragClient;
    private final AiInteractionMapper aiInteractionMapper;
    private final AuthzService authzService;
    private final IdempotencyService idempotencyService;
    private final ConsultationProperties properties;

    /** AI-API-002:已发布知识优先，资料不足时提供范围受限的办公 IT 通用建议。 */
    public AiChatResponse chat(CurrentUser user, String sessionId, AiChatRequest request,
                               String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        // AI 对话只发生在员工与 AI 之间,工程师不通过该接口介入
        authzService.requireCreator(user, consultation);
        requireAiActive(consultation);

        return idempotencyService.execute(user.userId(), OP_CHAT + ':' + sessionId, idempotencyKey,
                request, AiChatResponse.class,
                () -> doChat(user, sessionId, request, idempotencyKey)).value();
    }

    private AiChatResponse doChat(CurrentUser user, String sessionId, AiChatRequest request,
                                  String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        requireAiActive(consultation);

        // 员工提问先落库:即使后续 AI 降级,对话历史也完整(RD-013 不得用空成功掩盖失败)
        messageService.appendEmployeeMessage(sessionId, user.userId(),
                "ai-q:" + idempotencyKey, request.message());

        RagResult result = null;
        if (properties.getAi().isAnswerEnabled()) {
            RagQuery query = new RagQuery(sessionId, request.message(),
                    contextCategory(consultation, request), contextAsset(request),
                    properties.getAi().getTopK(), new RagCaller(user.userId(), user.role().name()));
            result = ragClient.answer(query, RequestContext.get());
        }

        // 模型调用耗时较长，期间员工可结束会话。只在落库阶段加锁，
        // 既不阻塞关闭，又保证关闭提交后不再追加 AI 回答。
        requireAiActive(transitionService.loadForUpdate(sessionId));

        AiAnswerGuard.Verdict verdict = AiAnswerGuard.evaluate(
                result, properties.getAi(),
                knowledgeQueryService::isPublishedCurrentVersion);

        String interactionId = persistInteraction(sessionId, result, verdict);
        persistAiMessage(sessionId, idempotencyKey, interactionId, verdict);

        if (verdict.replyType() == AiReplyType.REFUSE) {
            log.info("[ai] 拒答 session={} reason={} requestId={}",
                    sessionId, verdict.refusalReason(), RequestContext.get());
        }

        return new AiChatResponse(
                sessionId,
                verdict.replyType(),
                verdict.answerText(),
                verdict.citations(),
                verdict.confidence(),
                verdict.suggestTransfer(),
                verdict.refusalReason(),
                modelVersionOf(result),
                interactionId);
    }

    /** AI-006 AI_SESSION_NOT_ACTIVE:只有 AI_ACTIVE 的会话接受 AI 消息。 */
    private void requireAiActive(Consultation consultation) {
        if (consultation.getStatus() != ConsultationStatus.AI_ACTIVE) {
            throw new ApiException(ApiCode.AI_SESSION_NOT_ACTIVE,
                    "当前咨询状态不接受 AI 消息,请使用人工咨询或直接提交工单");
        }
    }

    private String contextCategory(Consultation consultation, AiChatRequest request) {
        if (request.contextRefs() != null && request.contextRefs().categoryId() != null) {
            return request.contextRefs().categoryId();
        }
        return consultation.getCategoryId();
    }

    private String contextAsset(AiChatRequest request) {
        return request.contextRefs() == null ? null : request.contextRefs().assetId();
    }

    private String modelVersionOf(RagResult result) {
        if (result != null && result.modelVersion() != null && !result.modelVersion().isBlank()) {
            return result.modelVersion();
        }
        return properties.getAi().getModelVersion();
    }

    /**
     * 写 AI 回答审计(PRD 17.2:保存模型版本、检索来源、知识版本、置信度、响应耗时)。
     * 不保存提示词与模型推理过程(AI-008)。
     */
    private String persistInteraction(String sessionId, RagResult result, AiAnswerGuard.Verdict verdict) {
        LocalDateTime now = Times.nowUtc();
        AiInteraction interaction = new AiInteraction();
        interaction.setInteractionId(Ids.interactionId());
        interaction.setSessionId(sessionId);
        interaction.setModelVersion(modelVersionOf(result));
        interaction.setRetrievedVersionsJson(Json.write(
                result == null || result.retrievedVersionIds() == null
                        ? List.of() : result.retrievedVersionIds()));
        interaction.setConfidence(verdict.confidence());
        interaction.setLatencyMs(result == null ? 0L : result.latencyMs());
        interaction.setOccurredAt(now);
        interaction.setCreatedAt(now);
        interaction.setUpdatedAt(now);
        aiInteractionMapper.insert(interaction);
        return interaction.getInteractionId();
    }

    private void persistAiMessage(String sessionId, String idempotencyKey, String interactionId,
                                  AiAnswerGuard.Verdict verdict) {
        boolean refused = verdict.replyType() == AiReplyType.REFUSE;
        String content = refused ? refusalTranscript(verdict) : verdict.answerText();
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("schemaVersion", 1);
        metadata.put("citations", verdict.citations());
        metadata.put("interactionId", interactionId);
        metadata.put("replyType", verdict.replyType());
        metadata.put("refusalReason", verdict.refusalReason());
        metadata.put("generalAnswer", verdict.replyType() == AiReplyType.ANSWER && verdict.citations().isEmpty());
        messageService.appendAiMessage(sessionId, "ai-a:" + idempotencyKey, content, Json.write(metadata));
    }

    private String refusalTranscript(AiAnswerGuard.Verdict verdict) {
        if (verdict.refusalReason() == com.itticket.consultation.enums.AiRefusalReason.OFF_TOPIC) {
            return "我只能协助办公 IT 问题，这个请求不在服务范围内，不能答复。";
        }
        if (verdict.refusalReason() == com.itticket.consultation.enums.AiRefusalReason.HIGH_RISK_TOPIC) {
            return "该请求涉及高风险操作或需要授权，请转人工处理；我不能执行操作或代为更改系统。";
        }
        return REFUSAL_TRANSCRIPT;
    }

    // ---------------------------------------------------------------- 反馈

    /**
     * AI-API-003:员工对某次 AI 回答给出反馈。
     *
     * <p>PRD 17.2 原策略:无帮助与内容错误的对话自动脱敏后进入知识优化队列。
     * <b>2026-09-29 冷启动修订</b>:有帮助的回答同样标记待知识优化处理——
     * 冷启动期知识库内容少,员工认可的通用能力回答是高质量沉淀来源,
     * 知识库管理员审核后可发布为正式知识,加速知识库建设。
     * 原始对话不自动训练、不自动入库、不自动发布;本服务只落 {@code ai_interaction.feedback},
     * queuedForOptimization=true 仅表示持久化的待处理反馈标记；当前尚无知识域消费者、
     * 脱敏任务或审核入库流程，不代表内容已经进入已实现的队列或完成脱敏入库。
     */
    public AiFeedbackResponse feedback(CurrentUser user, String sessionId, AiFeedbackRequest request,
                                       String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);

        return idempotencyService.execute(user.userId(), OP_FEEDBACK + ':' + sessionId, idempotencyKey,
                request, AiFeedbackResponse.class, () -> {
                    AiInteraction interaction = aiInteractionMapper.selectById(request.interactionId());
                    // 归属校验:不得对他人会话的交互记录写反馈(AX-001)
                    if (interaction == null || !sessionId.equals(interaction.getSessionId())) {
                        throw ApiException.notFound();
                    }
                    aiInteractionMapper.update(null, Wrappers.<AiInteraction>lambdaUpdate()
                            .eq(AiInteraction::getInteractionId, request.interactionId())
                            .set(AiInteraction::getFeedback, request.feedback())
                            .set(AiInteraction::getUpdatedAt, Times.nowUtc()));

                    // 持久化待处理反馈标记；未来知识域可消费，当前不自动脱敏、发布或训练。
                    boolean queued = true;
                    return new AiFeedbackResponse(request.interactionId(), true, queued);
                }).value();
    }
}
