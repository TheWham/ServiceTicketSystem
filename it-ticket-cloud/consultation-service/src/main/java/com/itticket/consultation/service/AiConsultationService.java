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
import com.itticket.consultation.dto.GovernanceTraceDto;
import com.itticket.consultation.dto.KnowledgeCitationDto;
import com.itticket.consultation.dto.TicketDraftDto;
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
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.consultation.adapter.RagCallContext;
import com.itticket.consultation.adapter.RagExecutionAudit;
import com.itticket.consultation.adapter.agent.PythonAgentClient;
import com.itticket.consultation.dto.AiStreamEvent;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;

import java.time.LocalDateTime;
import java.math.BigDecimal;
import com.itticket.consultation.enums.AiRefusalReason;
import java.util.List;
import java.util.ArrayList;
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
            "暂时无法给出可靠的 IT 建议，请转人工或直接提交工单。";

    private final ConsultationTransitionService transitionService;
    private final ConsultationMessageService messageService;
    private final KnowledgeQueryService knowledgeQueryService;
    private final GuardedRagClient ragClient;
    private final AiInteractionMapper aiInteractionMapper;
    private final AuthzService authzService;
    private final IdempotencyService idempotencyService;
    private final ConsultationProperties properties;
    private final PythonAgentClient pythonAgentClient;
    private final ObjectMapper json = new ObjectMapper();

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

    /**
     * AI-007 流式对话接口：建立 SSE 单向长连接，实时推送 answer_delta 增量并在完成时持久化。
     */
    public void chatStream(CurrentUser user, String sessionId, AiChatRequest request,
                           String idempotencyKey, SseEmitter emitter) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);
        requireAiActive(consultation);

        String currentClientMessageId = "ai-q:" + idempotencyKey;
        List<RagQuery.Turn> history = messageService.loadAiHistory(
                sessionId, consultation.getCreatorId(), currentClientMessageId,
                properties.getAi().getContextMaxMessages(), properties.getAi().getContextMaxChars());

        // 员工提问先落库
        messageService.appendEmployeeMessage(sessionId, user.userId(),
                currentClientMessageId, request.message());

        emitter.onTimeout(() -> {
            log.warn("SseEmitter timed out for session {}", sessionId);
            emitter.complete();
        });
        emitter.onError(err -> {
            log.error("SseEmitter error for session {}", sessionId, err);
        });

        CompletableFuture.runAsync(() -> {
            AtomicInteger seq = new AtomicInteger(1);
            try {
                if (pythonAgentClient != null && pythonAgentClient.enabled()) {
                    RagQuery query = new RagQuery(sessionId, request.message(), history,
                            contextCategory(consultation, request), contextAsset(request),
                            properties.getAi().getTopK(), new RagCaller(user.userId(), user.role().name()));

                    RagCallContext ragContext = new RagCallContext(RequestContext.get(),
                            System.nanoTime() + java.util.concurrent.TimeUnit.MILLISECONDS.toNanos(180000L),
                            new RagExecutionAudit());

                    pythonAgentClient.chatStream(query, List.of(), ragContext, frame -> {
                        try {
                            if ("delta".equals(frame.event())) {
                                JsonNode node = json.readTree(frame.data());
                                String deltaText = node.path("delta").asText("");
                                if (!deltaText.isEmpty()) {
                                    emitter.send(SseEmitter.event().name("answer_delta")
                                            .data(AiStreamEvent.delta(sessionId, seq.getAndIncrement(), deltaText)));
                                }
                            } else if ("stage".equals(frame.event())) {
                                JsonNode node = json.readTree(frame.data());
                                emitter.send(SseEmitter.event().name("stage").data(node));
                            } else if ("reasoning".equals(frame.event())) {
                                JsonNode node = json.readTree(frame.data());
                                String reasoningDelta = node.path("delta").asText("");
                                if (!reasoningDelta.isEmpty()) {
                                    emitter.send(SseEmitter.event().name("reasoning_delta")
                                            .data(AiStreamEvent.reasoning(sessionId, seq.getAndIncrement(), reasoningDelta)));
                                }
                            } else if ("done".equals(frame.event())) {
                                JsonNode doneNode = json.readTree(frame.data());
                                String answerText = doneNode.path("answerText").asText("");
                                String replyType = doneNode.path("replyType").asText("ANSWER");
                                double confidence = doneNode.path("confidence").asDouble(0.95);
                                boolean offTopic = doneNode.path("offTopic").asBoolean(false);

                                TicketDraftDto draft = null;
                                if (doneNode.has("ticketDraft") && doneNode.path("ticketDraft").isObject()) {
                                    draft = json.treeToValue(doneNode.path("ticketDraft"), TicketDraftDto.class);
                                }
                                GovernanceTraceDto trace = null;
                                if (doneNode.has("governanceTrace") && doneNode.path("governanceTrace").isObject()) {
                                    trace = json.treeToValue(doneNode.path("governanceTrace"), GovernanceTraceDto.class);
                                }

                                List<KnowledgeCitationDto> citations = new ArrayList<>();
                                if (doneNode.has("citations") && doneNode.path("citations").isArray()) {
                                    for (JsonNode cNode : doneNode.path("citations")) {
                                        citations.add(new KnowledgeCitationDto(
                                                cNode.path("articleId").asText(""),
                                                cNode.path("versionId").asText(""),
                                                cNode.path("title").asText(""),
                                                BigDecimal.valueOf(cNode.path("score").asDouble(1.0)),
                                                cNode.path("snippet").asText("")
                                        ));
                                    }
                                }

                                requireAiActive(transitionService.loadForUpdate(sessionId));

                                AiAnswerGuard.Verdict verdict = "REFUSE".equals(replyType)
                                        ? AiAnswerGuard.Verdict.refuse(offTopic ? AiRefusalReason.OFF_TOPIC : AiRefusalReason.NO_RELIABLE_KNOWLEDGE, BigDecimal.ZERO)
                                        : new AiAnswerGuard.Verdict(AiReplyType.ANSWER, answerText, citations, BigDecimal.valueOf(confidence), null, false);

                                String interactionId = persistInteraction(sessionId, null, verdict);
                                persistAiMessage(sessionId, idempotencyKey, interactionId, verdict, draft, trace);

                                Map<String, Object> completeData = new LinkedHashMap<>();
                                completeData.put("sessionId", sessionId);
                                completeData.put("replyType", verdict.replyType());
                                completeData.put("answer", verdict.answerText());
                                completeData.put("citations", verdict.citations());
                                completeData.put("confidence", verdict.confidence());
                                completeData.put("suggestTransfer", verdict.suggestTransfer());
                                completeData.put("ticketDraft", draft);
                                completeData.put("governanceTrace", trace);

                                emitter.send(SseEmitter.event().name("answer_completed")
                                        .data(AiStreamEvent.completed(sessionId, seq.getAndIncrement(), completeData)));
                                emitter.complete();
                            }
                        } catch (Exception ex) {
                            log.error("Failed handling SSE frame from agent", ex);
                        }
                    });
                } else {
                    AiChatResponse syncResp = doChat(user, sessionId, request, idempotencyKey);
                    if (syncResp.answerText() != null && !syncResp.answerText().isEmpty()) {
                        emitter.send(SseEmitter.event().name("answer_delta")
                                .data(AiStreamEvent.delta(sessionId, seq.getAndIncrement(), syncResp.answerText())));
                    }
                    Map<String, Object> completeData = new LinkedHashMap<>();
                    completeData.put("sessionId", sessionId);
                    completeData.put("replyType", syncResp.replyType());
                    completeData.put("answer", syncResp.answerText());
                    completeData.put("citations", syncResp.citations());
                    completeData.put("confidence", syncResp.confidence());
                    completeData.put("suggestTransfer", syncResp.suggestTransfer());
                    completeData.put("ticketDraft", syncResp.ticketDraft());
                    completeData.put("governanceTrace", syncResp.governanceTrace());

                    emitter.send(SseEmitter.event().name("answer_completed")
                            .data(AiStreamEvent.completed(sessionId, seq.getAndIncrement(), completeData)));
                    emitter.complete();
                }
            } catch (Exception e) {
                log.error("SSE chat stream execution error for session {}", sessionId, e);
                try {
                    emitter.send(SseEmitter.event().name("error")
                            .data(AiStreamEvent.error(sessionId, seq.getAndIncrement(), "AI_UNAVAILABLE", e.getMessage())));
                    emitter.complete();
                } catch (Exception ignored) {
                    emitter.completeWithError(e);
                }
            }
        });
    }

    private AiChatResponse doChat(CurrentUser user, String sessionId, AiChatRequest request,
                                  String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);
        requireAiActive(consultation);

        String currentClientMessageId = "ai-q:" + idempotencyKey;
        List<RagQuery.Turn> history = messageService.loadAiHistory(
                sessionId, consultation.getCreatorId(), currentClientMessageId,
                properties.getAi().getContextMaxMessages(), properties.getAi().getContextMaxChars());

        // 员工提问先落库:即使后续 AI 降级,对话历史也完整(RD-013 不得用空成功掩盖失败)
        messageService.appendEmployeeMessage(sessionId, user.userId(),
                currentClientMessageId, request.message());

        RagResult result = null;
        if (properties.getAi().isAnswerEnabled()) {
            RagQuery query = new RagQuery(sessionId, request.message(), history,
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

        // 建单草稿只在正常回答时透出(拒答不携带草稿);员工确认后才经 /ticket-draft/confirm 建单
        TicketDraftDto draft = verdict.replyType() == AiReplyType.REFUSE
                ? null : (result == null ? null : result.ticketDraft());

        GovernanceTraceDto trace = result == null ? null : result.governanceTrace();

        // 草稿与治理 Trace 要**随消息一起落库**，支持前端历史回放
        persistAiMessage(sessionId, idempotencyKey, interactionId, verdict, draft, trace);

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
                interactionId,
                draft,
                trace);
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
                                  AiAnswerGuard.Verdict verdict, TicketDraftDto draft, GovernanceTraceDto trace) {
        boolean refused = verdict.replyType() == AiReplyType.REFUSE;
        String content = refused ? refusalTranscript(verdict) : verdict.answerText();
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("schemaVersion", 1);
        metadata.put("citations", verdict.citations());
        metadata.put("interactionId", interactionId);
        metadata.put("replyType", verdict.replyType());
        metadata.put("refusalReason", verdict.refusalReason());
        metadata.put("generalAnswer", verdict.replyType() == AiReplyType.ANSWER && verdict.citations().isEmpty());
        // 追加式键：老读者（含 RefusalCaseMapper 的 JSON_EXTRACT）不受影响，schemaVersion 保持 1。
        if (draft != null) {
            metadata.put("ticketDraft", draft);
        }
        if (trace != null) {
            metadata.put("governanceTrace", trace);
        }
        messageService.appendAiMessage(sessionId, "ai-a:" + idempotencyKey, content, Json.write(metadata));
    }

    private String refusalTranscript(AiAnswerGuard.Verdict verdict) {
        if (verdict.refusalReason() == com.itticket.consultation.enums.AiRefusalReason.OFF_TOPIC) {
            return "我可以协助 IT 和电脑技术问题，这个请求不在服务范围内，不能答复。";
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
     * queuedForOptimization=true 表示持久化的待处理反馈标记，不代表审核完成。
     * rag-service 定时消费 HELPFUL 的通用回答，脱敏后提交知识审核；其他反馈保留供质量分析。
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

                    // 持久化反馈由知识域异步消费；不自动发布或训练。
                    boolean queued = true;
                    return new AiFeedbackResponse(request.interactionId(), true, queued);
                }).value();
    }
}
