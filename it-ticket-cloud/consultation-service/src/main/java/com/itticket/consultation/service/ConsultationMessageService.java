package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.consultation.adapter.RagQuery;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.api.FieldIssue;
import com.itticket.consultation.api.PagedData;
import com.itticket.consultation.dto.ContentRequest;
import com.itticket.consultation.dto.MessageProjection;
import com.itticket.consultation.entity.Assignment;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.enums.AssignmentEndReason;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.mapper.ConsultationMessageMapper;
import com.itticket.consultation.statemachine.ConsultationEvent;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Times;
import com.itticket.consultation.support.Json;
import com.itticket.consultation.statemachine.Actor;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 咨询消息(OpenAPI 05 sendHumanConsultationMessage / listConsultationMessages)。
 *
 * <p>消息是只追加事实。两类消息会触发状态迁移:
 * <ul>
 *   <li>当前责任工程师在 WAITING_ENGINEER 下发出的实际消息 = 首次有效回复 → HUMAN_ACTIVE
 *       (SM-CONSULT-001;打开、已读和系统消息都不算);</li>
 *   <li>员工在 PENDING_CONFIRMATION 下发出的消息 = 回复未解决 → HUMAN_ACTIVE,保留原结论。</li>
 * </ul>
 */
@Service
@RequiredArgsConstructor
public class ConsultationMessageService {

    private final ConsultationMessageMapper messageMapper;
    private final ConsultationTransitionService transitionService;
    private final AssignmentService assignmentService;
    private final ConsultationSlaService slaService;
    private final AuthzService authzService;
    private final ConsultationAttachmentService attachmentService;

    /** 人工咨询消息。仅会话参与者可发送(AX-006 SEND_MESSAGE)。 */
    @Transactional(propagation = Propagation.MANDATORY)
    public MessageProjection send(CurrentUser user, Consultation consultation, ContentRequest request) {
        authzService.requireParticipant(user, consultation);
        if (consultation.getStatus().isTerminal()) {
            throw new ApiException(ApiCode.ILLEGAL_STATE_TRANSITION, "咨询已处于终态,不能继续发送消息");
        }
        if (request.attachmentIds() != null && !request.attachmentIds().isEmpty()) {
            ConsultationAttachmentService.requireHumanState(consultation);
        }
        validateContent(request);

        Optional<ConsultationMessage> replayed =
                findByClientMessageId(consultation.getSessionId(), request.clientMessageId());
        if (replayed.isPresent()) {
            if (!user.userId().equals(replayed.get().getSenderId())) {
                throw new ApiException(ApiCode.IDEMPOTENCY_CONFLICT, "client_message_id 已被其他参与者使用");
            }
            // RD-002:消息发送不允许用重试覆盖正文,同一 clientMessageId 返回首次结果
            return MessageProjection.of(replayed.get());
        }

        boolean fromEngineer = !user.userId().equals(consultation.getCreatorId())
                && user.userId().equals(consultation.getCurrentEngineerId());
        MessageSenderType senderType = fromEngineer ? MessageSenderType.ENGINEER : MessageSenderType.EMPLOYEE;
        String messageId = Ids.messageId();
        String metadata = null;
        if (request.attachmentIds() != null && !request.attachmentIds().isEmpty()) {
            var attachments = attachmentService.bind(user, consultation, messageId, request.attachmentIds());
            metadata = Json.write(Map.of("schemaVersion", 1, "attachments", attachments));
        }
        ConsultationMessage message = append(messageId, consultation.getSessionId(), user.userId(), senderType,
                request.clientMessageId(), request.content() == null ? "" : request.content(), metadata);

        applyMessageDrivenTransition(user, consultation, message, fromEngineer);
        return MessageProjection.of(message);
    }

    /** OpenAPI 05 Content 的 anyOf 要求 content 或 attachment_ids 至少其一。 */
    private void validateContent(ContentRequest request) {
        ConsultationAttachmentService.validateIds(request.attachmentIds());
        if (!request.isPayloadPresent()) {
            throw ApiException.validation(List.of(FieldIssue.required("content", "消息内容不能为空")));
        }
    }

    private void applyMessageDrivenTransition(CurrentUser user, Consultation consultation,
                                              ConsultationMessage message, boolean fromEngineer) {
        ConsultationStatus status = consultation.getStatus();

        if (fromEngineer && status == ConsultationStatus.WAITING_ENGINEER) {
            transitionService.apply(consultation, TransitionSpec.builder()
                    .event(ConsultationEvent.CONSULTATION_RESPOND)
                    .actor(user)
                    .reason("工程师首次有效回复")
                    .eventPayload(Map.of(
                            "session_id", consultation.getSessionId(),
                            "message_id", message.getMessageId()))
                    .build());
            // 副作用:结束当前分配任务并记录响应时间(SM-CONSULT-001 业务副作用列)
            Optional<Assignment> active = assignmentService.activeAssignment(consultation.getSessionId());
            LocalDateTime startedAt = active.map(Assignment::getAssignedAt).orElse(null);
            active.ifPresent(assignment -> assignmentService.endAssignment(
                    assignment.getAssignmentId(), AssignmentEndReason.RESPONDED, message.getSentAt()));
            slaService.markResponded(consultation.getSessionId(), startedAt, message.getSentAt());
            return;
        }

        if (!fromEngineer && status == ConsultationStatus.PENDING_CONFIRMATION) {
            transitionService.apply(consultation, TransitionSpec.builder()
                    .event(ConsultationEvent.CONSULTATION_REJECT_RESOLUTION)
                    // Only this authenticated session creator acts as its requester, regardless of global role.
                    .actor(new CurrentUser(user.userId(), user.role(), Actor.EMPLOYEE))
                    .reason("员工回复未解决")
                    .build());
        }
    }

    /** AI 回答落库。AI 不是会话参与者,senderId 为空,引用列表随消息一并保存。 */
    public ConsultationMessage appendAiMessage(String sessionId, String clientMessageId,
                                               String content, String citationJson) {
        return append(sessionId, null, MessageSenderType.AI, clientMessageId, content, citationJson);
    }

    /** 系统消息(如工程师结论通知)。系统消息不计入首次有效响应。 */
    public ConsultationMessage appendSystemMessage(String sessionId, String clientMessageId, String content) {
        return append(sessionId, null, MessageSenderType.SYSTEM, clientMessageId, content, null);
    }

    /** 员工向 AI 提出的问题,作为员工消息追加(AI 对话与人工对话共用同一条会话记录)。 */
    public ConsultationMessage appendEmployeeMessage(String sessionId, String employeeId,
                                                     String clientMessageId, String content) {
        return append(sessionId, employeeId, MessageSenderType.EMPLOYEE, clientMessageId, content, null);
    }

    /** 工程师提交的解决结论,作为工程师消息追加,便于员工在同一会话内查看。 */
    public ConsultationMessage appendEngineerMessage(String sessionId, String engineerId,
                                                     String clientMessageId, String content) {
        return append(sessionId, engineerId, MessageSenderType.ENGINEER, clientMessageId, content, null);
    }

    private ConsultationMessage append(String sessionId, String senderId, MessageSenderType senderType,
                                       String clientMessageId, String content, String citationJson) {
        return append(Ids.messageId(), sessionId, senderId, senderType, clientMessageId, content, citationJson);
    }

    private ConsultationMessage append(String messageId, String sessionId, String senderId, MessageSenderType senderType,
                                       String clientMessageId, String content, String citationJson) {
        LocalDateTime now = Times.nowUtc();
        ConsultationMessage message = new ConsultationMessage();
        message.setMessageId(messageId);
        message.setSessionId(sessionId);
        message.setSenderId(senderId);
        message.setSenderType(senderType);
        message.setClientMessageId(clientMessageId);
        message.setContent(content);
        message.setCitationJson(citationJson);
        message.setSentAt(now);
        message.setCreatedAt(now);
        message.setUpdatedAt(now);
        messageMapper.insert(message);
        return message;
    }

    private Optional<ConsultationMessage> findByClientMessageId(String sessionId, String clientMessageId) {
        return Optional.ofNullable(messageMapper.selectOne(Wrappers.<ConsultationMessage>lambdaQuery()
                .eq(ConsultationMessage::getSessionId, sessionId)
                .eq(ConsultationMessage::getClientMessageId, clientMessageId)));
    }

    /** READ_CHAT:仅会话参与者可读聊天正文(PRD 5.2、AX-006)。 */
    public PagedData<MessageProjection> list(CurrentUser user, Consultation consultation,
                                             int page, int pageSize) {
        authzService.requireParticipant(user, consultation);
        IPage<ConsultationMessage> result = messageMapper.selectPage(
                new Page<>(page, pageSize),
                Wrappers.<ConsultationMessage>lambdaQuery()
                        .eq(ConsultationMessage::getSessionId, consultation.getSessionId())
                        .orderByAsc(ConsultationMessage::getSentAt)
                        .orderByAsc(ConsultationMessage::getMessageId));
        List<MessageProjection> items = result.getRecords().stream()
                .map(MessageProjection::of)
                .toList();
        return new PagedData<>(items, page, pageSize, result.getTotal());
    }

    /** 转单预填用:按时间顺序加载会话消息(封顶 200 条),不经过 READ_CHAT 鉴权,由调用方负责。 */
    public List<ConsultationMessage> loadTimeline(String sessionId) {
        return messageMapper.selectList(Wrappers.<ConsultationMessage>lambdaQuery()
                .eq(ConsultationMessage::getSessionId, sessionId)
                .orderByAsc(ConsultationMessage::getSentAt)
                .orderByAsc(ConsultationMessage::getMessageId)
                .last("LIMIT 200"));
    }

    /**
     * Load context only after the caller has authorized the session creator.
     * Select newest AI messages first, retain their text within the budget, then restore chronology.
     * Nonpositive limits use defaults; oversized limits are capped regardless of configuration.
     */
    public List<RagQuery.Turn> loadAiHistory(String sessionId, String creatorId,
                                            String currentClientMessageId, int maxMessages, int maxChars) {
        int messageLimit = maxMessages <= 0 ? 12 : Math.min(maxMessages, 40);
        int remaining = maxChars <= 0 ? 12000 : Math.min(maxChars, 32000);
        List<ConsultationMessage> messages = messageMapper.selectAiHistory(
                sessionId, creatorId, currentClientMessageId, messageLimit);
        List<RagQuery.Turn> turns = new ArrayList<>();
        for (ConsultationMessage message : messages) {
            String content = message.getContent();
            if (content == null || content.isBlank()) {
                continue;
            }
            int length = Math.min(content.length(), remaining);
            // Do not send an unpaired UTF-16 surrogate when truncating a message.
            if (length < content.length() && length > 0
                    && Character.isHighSurrogate(content.charAt(length - 1))
                    && Character.isLowSurrogate(content.charAt(length))) {
                length--;
            }
            if (length > 0) {
                String role = message.getSenderType() == MessageSenderType.EMPLOYEE ? "user" : "assistant";
                turns.add(new RagQuery.Turn(role, content.substring(0, length)));
            }
            remaining -= length;
            if (remaining == 0 || length < content.length()) {
                break;
            }
        }
        Collections.reverse(turns);
        return List.copyOf(turns);
    }
}
