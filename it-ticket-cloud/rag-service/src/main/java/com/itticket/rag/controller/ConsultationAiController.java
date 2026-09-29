package com.itticket.rag.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.rag.config.EmbeddingProperties;
import com.itticket.rag.dto.ai.AiChatRequest;
import com.itticket.rag.dto.ai.AiChatResponse;
import com.itticket.rag.dto.ai.KnowledgeCitation;
import com.itticket.rag.entity.AiInteraction;
import com.itticket.rag.enums.AiRefusalReason;
import com.itticket.rag.enums.AiReplyType;
import com.itticket.rag.mapper.AiInteractionMapper;
import com.itticket.rag.service.RagRetrievalService;
import com.itticket.rag.support.Ids;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.List;

/**
 * ============================================================================
 * AI 消息检索侧接口 (ConsultationAiController)
 * ============================================================================
 *
 * 【职责边界（重要）】：
 * 本模块只做 RAG 检索与知识策略判定，**不承担大模型生成与对话状态**。该端点按契约
 * AI-API-002 的路径与响应结构提供「检索侧结果」：
 * - 强制只检索 status=PUBLISHED 的知识（AI-001 / AC-27）；
 * - 高风险主题直接拦截（HIGH_RISK_TOPIC）；
 * - 相似度低于阈值时给出 NO_RELIABLE_KNOWLEDGE / LOW_CONFIDENCE；
 * - 命中可靠知识时以 citations 交付引用与 confidence，**不输出 answerText**——
 *   回答生成与 suggestTransfer 的业务决策由 AI 客服服务完成（本模块以 POLICY_BLOCKED
 *   表明"生成不在此服务"）。
 *
 * 【会话归属】会话生命周期由 AI 客服服务负责，本服务不校验会话存在，只以路径 sessionId
 * 作为审计归属（ai_interaction.session_id），并回填 interactionId 供后续反馈关联。
 *
 * 【幂等说明】契约 AI-002 要求发送消息带 Idempotency-Key。本模块不做会话与消息落库，
 * 该请求头仅记录日志，严格幂等由会话属主（AI 客服服务）实现。
 *
 * @author IT工单系统研发组 - RAG专项
 */
@Slf4j
@RestController
@RequestMapping("/api/v1/consultations")
@RequiredArgsConstructor
public class ConsultationAiController {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final RagRetrievalService retrievalService;
    private final AiInteractionMapper aiInteractionMapper;
    private final EmbeddingProperties embeddingProperties;

    /**
     * AI 消息：返回检索依据与策略判定（不调用大模型）。
     *
     * @param sessionId      会话 ID（路径），长度 1-32
     * @param request        提问请求体（契约 AI-004.2）
     * @param requestId      可选链路 ID
     * @param idempotencyKey 可选幂等键，仅记录
     */
    @PostMapping("/{id}/ai-messages")
    public Result<AiChatResponse> postAiMessage(
            @PathVariable("id") String sessionId,
            @Valid @RequestBody AiChatRequest request,
            @RequestHeader(value = "X-Request-Id", required = false) String requestId,
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey) {

        UserContext.CurrentUser user = UserContext.get();
        if (!Ids.fits(sessionId)) {
            throw new BizException(ErrorCode.PARAM_INVALID, "sessionId 非法：长度需为 1-32 个字符");
        }
        if (idempotencyKey != null && !idempotencyKey.isBlank()) {
            log.info("ai-messages idempotency key received (not enforced by RAG service): {}", idempotencyKey);
        }

        long startMs = System.currentTimeMillis();
        String interactionId = Ids.next("ai");
        String modelVersion = retrievalModelTag();
        String categoryId = request.contextRefs() == null ? null : request.contextRefs().categoryId();

        log.info("AI message retrieval: sessionId={}, operator={}, requestId={}, categoryId={}",
                sessionId, user.getUserId(), requestId, categoryId);

        RagRetrievalService.RetrievalOutcome outcome =
                retrievalService.retrieve(request.message(), categoryId, null);
        BigDecimal confidence = scale(outcome.topSimilarity());

        AiChatResponse response;
        List<KnowledgeCitation> citations = List.of();
        if (outcome.highRiskBlocked()) {
            response = AiChatResponse.refuse(sessionId, AiRefusalReason.HIGH_RISK_TOPIC, confidence, true,
                    modelVersion, interactionId);
        } else if (outcome.dependencyUnavailable()) {
            response = AiChatResponse.refuse(sessionId, AiRefusalReason.MODEL_UNAVAILABLE, confidence, true,
                    modelVersion, interactionId);
        } else {
            citations = retrievalService.buildVerifiedCitations(outcome.hits());
            if (outcome.suggestedRefusalReason() != null) {
                response = AiChatResponse.refuse(sessionId, outcome.suggestedRefusalReason(), confidence, true,
                        modelVersion, interactionId, citations);
            } else if (citations.isEmpty()) {
                // 相似度达标但引用复核全部失效（版本已下线）→ 视为无可靠知识（AI-008）
                response = AiChatResponse.refuse(sessionId, AiRefusalReason.NO_RELIABLE_KNOWLEDGE, confidence, true,
                        modelVersion, interactionId);
            } else {
                // 检索可靠：交付引用与置信度，由 AI 客服服务生成回答
                response = AiChatResponse.refuse(sessionId, AiRefusalReason.POLICY_BLOCKED, confidence, false,
                        modelVersion, interactionId, citations);
            }
        }

        long latency = System.currentTimeMillis() - startMs;
        // 本端点不生成回答，因此审计一律记为拒答（回答审计由 AI 客服服务自行落库）
        boolean refused = response.replyType() == AiReplyType.REFUSE;
        audit(interactionId, sessionId, modelVersion, citations, confidence, refused, latency);

        return Result.ok(response);
    }

    // ---------------------------------------------------------------- 内部

    /** 审计落库（PENDING 失败不影响主链路，RD-013） */
    private void audit(String interactionId, String sessionId, String modelVersion,
                       List<KnowledgeCitation> citations, BigDecimal confidence, boolean refused, long latencyMs) {
        try {
            AiInteraction interaction = new AiInteraction();
            interaction.setInteractionId(interactionId);
            interaction.setSessionId(sessionId);
            interaction.setModelVersion(modelVersion);
            interaction.setRetrievedVersions(citationsJson(citations));
            interaction.setAnswer(null);
            interaction.setConfidence(confidence);
            interaction.setRefused(refused);
            interaction.setLatency((int) Math.min(latencyMs, Integer.MAX_VALUE));
            interaction.setCreatedAt(LocalDateTime.now());
            aiInteractionMapper.insert(interaction);
        } catch (Exception e) {
            log.warn("AI 交互审计写入失败（不影响响应）: interactionId={}, reason={}", interactionId, e.getMessage());
        }
    }

    /** 引用精简 JSON：article_id / version_id / score，截断至列长 500 */
    private String citationsJson(List<KnowledgeCitation> citations) {
        if (citations == null || citations.isEmpty()) {
            return "[]";
        }
        ArrayNode array = MAPPER.createArrayNode();
        for (KnowledgeCitation citation : citations) {
            ObjectNode node = array.addObject();
            node.put("a", citation.articleId());
            node.put("v", citation.versionId());
            if (citation.score() != null) {
                node.put("s", citation.score());
            }
        }
        String json = array.toString();
        return json.length() <= 500 ? json : json.substring(0, 500);
    }

    /** 检索引擎标识：本服务只涉及向量模型，回答模型由 AI 客服服务负责 */
    private String retrievalModelTag() {
        String embeddingModel = embeddingProperties.getModel();
        String tag = "rag-retrieval:" + (embeddingModel == null || embeddingModel.isBlank() ? "default" : embeddingModel);
        return tag.length() > 128 ? tag.substring(0, 128) : tag;
    }

    private BigDecimal scale(BigDecimal value) {
        BigDecimal safe = value == null ? BigDecimal.ZERO : value;
        return safe.setScale(4, RoundingMode.HALF_UP);
    }
}
