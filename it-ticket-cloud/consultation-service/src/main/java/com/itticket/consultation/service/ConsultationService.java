package com.itticket.consultation.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.consultation.api.ApiCode;
import com.itticket.consultation.api.ApiException;
import com.itticket.consultation.api.FieldIssue;
import com.itticket.consultation.api.PagedData;
import com.itticket.consultation.config.ConsultationProperties;
import com.itticket.consultation.dto.ConsultationCreatedResponse;
import com.itticket.consultation.dto.ConsultationProjection;
import com.itticket.consultation.dto.ConsultationResolutionRequest;
import com.itticket.consultation.dto.CreateConsultationRequest;
import com.itticket.consultation.dto.ReasonRequest;
import com.itticket.consultation.dto.QueueStatusResponse;
import com.itticket.consultation.dto.TicketDraftResponse;
import com.itticket.consultation.dto.TransferRequest;
import com.itticket.consultation.dto.TransferResponse;
import com.itticket.consultation.entity.Assignment;
import com.itticket.consultation.entity.Consultation;
import com.itticket.consultation.entity.ConsultationMessage;
import com.itticket.consultation.entity.ExceptionQueueItem;
import com.itticket.consultation.enums.ConsultationResolutionType;
import com.itticket.consultation.enums.ConsultationSource;
import com.itticket.consultation.enums.ConsultationStatus;
import com.itticket.consultation.enums.MessageSenderType;
import com.itticket.consultation.mapper.ConsultationMapper;
import com.itticket.consultation.statemachine.ConsultationEvent;
import com.itticket.consultation.statemachine.ConsultationStateMachine;
import com.itticket.consultation.statemachine.TransitionDecision;
import com.itticket.consultation.support.Ids;
import com.itticket.consultation.support.Times;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 咨询会话编排(AI-API-001/004、OpenAPI 05 的 /consultations 系列)。
 *
 * <p>本类负责把一次请求拆成:鉴权 → 幂等 → 状态迁移 → 副作用(分配、SLA、消息)。
 * 状态合法性全部下沉到 {@link ConsultationStateMachine},本类不再重复判断状态组合。
 *
 * <p>幂等:所有写接口都经过 {@link IdempotencyService},业务写入与幂等记录同事务提交(RD-002)。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ConsultationService {

    private static final String OP_CREATE = "CONSULTATION_CREATE";
    private static final String OP_TRANSFER = "CONSULTATION_TRANSFER";
    private static final String OP_CLOSE = "CONSULTATION_CLOSE";
    private static final String OP_REOPEN = "CONSULTATION_REOPEN";
    private static final String OP_CONFIRM = "CONSULTATION_CONFIRM";
    private static final String OP_RESOLUTION = "CONSULTATION_RESOLUTION";
    private static final String OP_CONVERT = "CONSULTATION_CONVERT";
    private static final String OP_MESSAGE = "CONSULTATION_MESSAGE";

    private final ConsultationMapper consultationMapper;
    private final ConsultationTransitionService transitionService;
    private final ConsultationMessageService messageService;
    private final AssignmentService assignmentService;
    private final ConsultationSlaService slaService;
    private final AuthzService authzService;
    private final IdempotencyService idempotencyService;
    private final OutboxService outboxService;
    private final ConsultationProperties properties;

    // ---------------------------------------------------------------- 创建

    /**
     * AI-API-001 创建咨询。只创建咨询,不创建工单。
     *
     * <p>source=AI 走"开始 AI 咨询"起点;HUMAN_DIRECT 与 TICKET_FOLLOW_UP 走"跳过 AI 转人工"起点,
     * 后者需要员工已确认分类(SM-CONSULT-001 守卫条件)。
     * TICKET_FOLLOW_UP 在 SM 中没有独立起点行,这里按"需要人工跟进"归入人工起点,
     * 属于实现解读,已在交付说明中标注待确认。
     */
    public ConsultationCreatedResponse create(CurrentUser user, CreateConsultationRequest request,
                                              String idempotencyKey) {
        ConsultationEvent event = request.source() == ConsultationSource.AI
                ? ConsultationEvent.CONSULTATION_START_AI
                : ConsultationEvent.CONSULTATION_START_HUMAN;

        TransitionDecision decision = ConsultationStateMachine.evaluate(null, event, user.actor());
        if (!decision.allowed()) {
            throw new ApiException(decision.failureCode(), decision.message());
        }
        if (event == ConsultationEvent.CONSULTATION_START_HUMAN
                && (request.categoryId() == null || request.categoryId().isBlank())) {
            throw ApiException.validation(List.of(FieldIssue.required("categoryId",
                    "跳过 AI 直接转人工必须先确认咨询分类")));
        }

        return idempotencyService.execute(user.userId(), OP_CREATE, idempotencyKey, request,
                ConsultationCreatedResponse.class,
                () -> doCreate(user, request, event, decision.to())).value();
    }

    private ConsultationCreatedResponse doCreate(CurrentUser user, CreateConsultationRequest request,
                                                 ConsultationEvent event, ConsultationStatus initialStatus) {
        LocalDateTime now = Times.nowUtc();
        Consultation consultation = new Consultation();
        consultation.setSessionId(Ids.sessionId());
        consultation.setCreatorId(user.userId());
        consultation.setCategoryId(request.categoryId());
        consultation.setStatus(initialStatus);
        consultation.setSource(request.source());
        consultation.setVersion(0L);
        consultation.setCreatedAt(now);
        consultation.setUpdatedAt(now);
        consultationMapper.insert(consultation);

        if (event == ConsultationEvent.CONSULTATION_START_HUMAN) {
            dispatchToHuman(consultation, user, now);
        }
        return new ConsultationCreatedResponse(consultation.getSessionId(),
                consultation.getStatus(), Times.iso(now));
    }

    // ---------------------------------------------------------------- 转人工

    /**
     * AI-API-004 转人工。不接受员工指定工程师。
     *
     * <p>已经处于 WAITING_ENGINEER 时按幂等成功返回当前分配,不重复创建分配任务
     * (SM-001:同一事件重复提交必须是幂等成功)。
     */
    public TransferResponse transfer(CurrentUser user, String sessionId, TransferRequest request,
                                     String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);

        if (consultation.getStatus() == ConsultationStatus.WAITING_ENGINEER) {
            Optional<Assignment> active = assignmentService.activeAssignment(sessionId);
            return new TransferResponse(sessionId, ConsultationStatus.WAITING_ENGINEER,
                    active.map(Assignment::getAssignmentId).orElse(null),
                    assignmentService.estimatedWaitSeconds(active.orElse(null), Times.nowUtc()));
        }

        return idempotencyService.execute(user.userId(), OP_TRANSFER + ':' + sessionId, idempotencyKey,
                request, TransferResponse.class,
                () -> doTransfer(user, sessionId, request)).value();
    }

    private TransferResponse doTransfer(CurrentUser user, String sessionId, TransferRequest request) {
        // 事务内重新读取,保证守卫基于最新状态与版本(SM-001)
        Consultation consultation = transitionService.load(sessionId);
        LocalDateTime now = Times.nowUtc();

        Consultation after = transitionService.apply(consultation, TransitionSpec.builder()
                .event(ConsultationEvent.CONSULTATION_TRANSFER)
                .actor(user)
                .reason("员工请求转人工")
                .setCategoryId(true)
                .categoryId(request.categoryId())
                // CONSULTATION_TRANSFERRED 的 assignment_id 只有分配之后才有,推迟到 dispatchToHuman 发
                .deferEvent(true)
                .build());

        Optional<Assignment> assignment = dispatchToHuman(after, user, now);
        return new TransferResponse(sessionId, ConsultationStatus.WAITING_ENGINEER,
                assignment.map(Assignment::getAssignmentId).orElse(null),
                assignmentService.estimatedWaitSeconds(assignment.orElse(null), now));
    }

    /**
     * 进入 WAITING_ENGINEER 后的共同副作用:分配候选工程师、启动响应 SLA、发 CONSULTATION_TRANSFERRED。
     *
     * <p>无候选人时按 RD-005 进异常队列并保持 WAITING_ENGINEER —— 不把分配失败写成咨询终态,
     * 也不阻塞员工继续提单(RD-013)。此时不发领域事件:EV-008 的 consultationTransferred
     * 把 assignment_id 列为必填,没有分配任务就无法构造合法 payload,事实由异常队列与审计承载。
     */
    private Optional<Assignment> dispatchToHuman(Consultation consultation, CurrentUser user, LocalDateTime now) {
        String categoryId = consultation.getCategoryId();
        Optional<Assignment> assignment = assignmentService.assignNextCandidate(
                consultation.getSessionId(), categoryId, now);

        slaService.startOrRestart(consultation.getSessionId(), now);

        if (assignment.isEmpty()) {
            assignmentService.enqueueException(consultation.getSessionId(),
                    ExceptionQueueItem.REASON_NO_ROUTE,
                    "分类 " + categoryId + " 无可用候选工程师,需平台管理员介入");
            log.warn("[transfer] 咨询 {} 分类 {} 无可用候选工程师", consultation.getSessionId(), categoryId);
            return Optional.empty();
        }

        bindEngineer(consultation, assignment.get());
        // payload 三个字段都是 EV-008 的必填项,此时才齐备;版本取绑定责任人后的最新版本
        outboxService.appendConsultation("CONSULTATION_TRANSFERRED", consultation.getSessionId(),
                consultation.getVersion(),
                Map.of("session_id", consultation.getSessionId(),
                        "category_id", categoryId,
                        "assignment_id", assignment.get().getAssignmentId()),
                "USER", user.userId());
        return assignment;
    }

    /** 把分配结果写回咨询投影,并发出 CONSULTATION_TRANSFERRED。 */
    private void bindEngineer(Consultation consultation, Assignment assignment) {
        LocalDateTime now = Times.nowUtc();
        int rows = consultationMapper.update(null, Wrappers.<Consultation>lambdaUpdate()
                .eq(Consultation::getSessionId, consultation.getSessionId())
                .eq(Consultation::getVersion, consultation.getVersion())
                .set(Consultation::getCurrentEngineerId, assignment.getEngineerId())
                .set(Consultation::getVersion, consultation.getVersion() + 1)
                .set(Consultation::getUpdatedAt, now));
        if (rows == 0) {
            throw new ApiException(ApiCode.ASSIGNMENT_CHANGED, "咨询已被其他操作变更,请重新读取后再试");
        }
        consultation.setCurrentEngineerId(assignment.getEngineerId());
        consultation.setVersion(consultation.getVersion() + 1);
    }

    // ---------------------------------------------------------------- 人工消息

    /**
     * 发送人工咨询消息(OpenAPI 05 sendHumanConsultationMessage)。
     *
     * <p>消息本身可能触发状态迁移(工程师首次有效回复、员工回复未解决),
     * 因此与消息写入放在同一幂等事务内,避免出现"消息已存在但状态没变"的半完成态。
     */
    public com.itticket.consultation.dto.MessageProjection sendMessage(
            CurrentUser user, String sessionId,
            com.itticket.consultation.dto.ContentRequest request, String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireParticipant(user, consultation);

        return idempotencyService.execute(user.userId(), OP_MESSAGE + ':' + sessionId, idempotencyKey,
                request, com.itticket.consultation.dto.MessageProjection.class, () -> {
                    Consultation current = transitionService.loadForUpdate(sessionId);
                    return messageService.send(user, current, request);
                }).value();
    }

    // ---------------------------------------------------------------- 结论与确认

    /** 工程师提交解决结论:HUMAN_ACTIVE → PENDING_CONFIRMATION(结论非空)。 */
    public ConsultationProjection submitResolution(CurrentUser user, String sessionId,
                                                   ConsultationResolutionRequest request,
                                                   String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCurrentEngineer(user, consultation);

        return idempotencyService.execute(user.userId(), OP_RESOLUTION + ':' + sessionId, idempotencyKey,
                request, ConsultationProjection.class, () -> {
                    Consultation current = transitionService.load(sessionId);
                    authzService.requireCurrentEngineer(user, current);
                    messageService.appendEngineerMessage(sessionId, user.userId(),
                            "resolution:" + idempotencyKey, request.conclusion());
                    Consultation after = transitionService.apply(current, TransitionSpec.builder()
                            .event(ConsultationEvent.CONSULTATION_SUBMIT_RESOLUTION)
                            .actor(user)
                            .reason("工程师提交解决结论")
                            .build());
                    return ConsultationProjection.of(after);
                }).value();
    }

    /**
     * 员工确认解决:PENDING_CONFIRMATION → RESOLVED。
     *
     * <p>契约缺口:SM-CONSULT-001 明确了这条迁移,但 OpenAPI 05 与 AI-005 都没有对应路径,
     * 这里补 {@code POST /consultations/{id}/confirmation},已在交付说明中列为需要回写 05 的项。
     */
    public ConsultationProjection confirmResolution(CurrentUser user, String sessionId, String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);

        return idempotencyService.execute(user.userId(), OP_CONFIRM + ':' + sessionId, idempotencyKey,
                Map.of("sessionId", sessionId), ConsultationProjection.class, () -> {
                    Consultation current = transitionService.load(sessionId);
                    Consultation after = resolve(current, user,
                            ConsultationResolutionType.EMPLOYEE_CONFIRMED,
                            ConsultationEvent.CONSULTATION_CONFIRM_RESOLVED, "员工确认解决");
                    return ConsultationProjection.of(after);
                }).value();
    }

    /** 员工确认与系统自动解决共用的收尾动作。供自动解决调度器复用,因此是 public。 */
    public Consultation resolve(Consultation current, CurrentUser actor,
                         ConsultationResolutionType resolutionType,
                         ConsultationEvent event, String reason) {
        LocalDateTime now = Times.nowUtc();
        Consultation after = transitionService.apply(current, TransitionSpec.builder()
                .event(event)
                .actor(actor)
                .reason(reason)
                .setResolutionType(true)
                .resolutionType(resolutionType)
                .setClosedAt(true)
                .closedAt(now)
                .eventPayload(Map.of(
                        "session_id", current.getSessionId(),
                        "resolved_type", resolutionType.getValue()))
                .build());
        slaService.cancel(current.getSessionId());
        return after;
    }

    // ---------------------------------------------------------------- 结束与恢复

    /** 员工主动结束:任意非终态 → CLOSED,无需员工填写原因。 */
    public ConsultationProjection close(CurrentUser user, String sessionId, String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);

        return idempotencyService.execute(user.userId(), OP_CLOSE + ':' + sessionId, idempotencyKey,
                Map.of("sessionId", sessionId), ConsultationProjection.class, () -> {
                    Consultation current = transitionService.loadForUpdate(sessionId);
                    if (current.getStatus() == ConsultationStatus.CLOSED) {
                        return ConsultationProjection.of(current);
                    }
                    LocalDateTime now = Times.nowUtc();
                    Consultation after = transitionService.apply(current, TransitionSpec.builder()
                            .event(ConsultationEvent.CONSULTATION_CLOSE)
                            .actor(user)
                            .reason("员工主动结束咨询")
                            .setClosedAt(true)
                            .closedAt(now)
                            .build());
                    endActiveAssignment(sessionId);
                    slaService.cancel(sessionId);
                    messageService.appendSystemMessage(sessionId, "close:" + after.getVersion(),
                            "员工已结束对话，会话已断开。");
                    return ConsultationProjection.of(after);
                }).value();
    }

    /**
     * 恢复咨询:RESOLVED → WAITING_ENGINEER,窗口 24 小时(SM-CONSULT-001)。
     * 优先分配原工程师,不可用时重新路由;响应 SLA 重新计时(PRD 8.3)。
     */
    public ConsultationProjection reopen(CurrentUser user, String sessionId, ReasonRequest request,
                                         String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);
        requireReopenWindow(consultation);

        return idempotencyService.execute(user.userId(), OP_REOPEN + ':' + sessionId, idempotencyKey,
                request, ConsultationProjection.class, () -> {
                    Consultation current = transitionService.load(sessionId);
                    requireReopenWindow(current);
                    LocalDateTime now = Times.nowUtc();
                    String originalEngineer = current.getCurrentEngineerId();

                    Consultation after = transitionService.apply(current, TransitionSpec.builder()
                            .event(ConsultationEvent.CONSULTATION_REOPEN)
                            .actor(user)
                            .reason(request.reason())
                            .setResolutionType(true)
                            .resolutionType(null)
                            .setClosedAt(true)
                            .closedAt(null)
                            .setEngineer(true)
                            .engineerId(null)
                            .eventPayload(Map.of(
                                    "session_id", sessionId,
                                    "reopen_reason", request.reason()))
                            .build());

                    Optional<Assignment> assignment = assignmentService
                            .assignPreferred(sessionId, originalEngineer, now);
                    if (assignment.isEmpty()) {
                        assignment = assignmentService.assignNextCandidate(
                                sessionId, after.getCategoryId(), now);
                    }
                    slaService.startOrRestart(sessionId, now);
                    if (assignment.isEmpty()) {
                        assignmentService.enqueueException(sessionId,
                                ExceptionQueueItem.REASON_NO_ROUTE,
                                "恢复咨询后无可用候选工程师,需平台管理员介入");
                    } else {
                        bindEngineer(after, assignment.get());
                    }
                    return ConsultationProjection.of(transitionService.load(sessionId));
                }).value();
    }

    /** SM-CONSULT-001:仅 RESOLVED 允许恢复,且必须在窗口内、未转工单。 */
    private void requireReopenWindow(Consultation consultation) {
        if (consultation.getStatus() != ConsultationStatus.RESOLVED) {
            throw new ApiException(ApiCode.ILLEGAL_STATE_TRANSITION, "只有已解决的咨询可以在窗口内恢复");
        }
        LocalDateTime resolvedAt = consultation.getClosedAt() == null
                ? consultation.getUpdatedAt() : consultation.getClosedAt();
        long hours = properties.getLifecycle().getReopenWindowHours();
        if (Duration.between(resolvedAt, Times.nowUtc()).toHours() >= hours) {
            throw new ApiException(ApiCode.ILLEGAL_STATE_TRANSITION,
                    "已超过 " + hours + " 小时恢复窗口");
        }
    }

    // ---------------------------------------------------------------- 转工单

    /**
     * 标记咨询已转为正式工单:任意非终态 → CONVERTED_TO_TICKET。
     *
     * <p>工单本身由 ticket-service 创建(AI-001 明确 AI 不得创建工单,咨询服务也不拥有工单事实)。
     * 本方法供 ticket-service 在工单创建成功后回调,入参 ticketId 即新建工单号。
     */
    public ConsultationProjection markConverted(CurrentUser user, String sessionId, String ticketId,
                                                String idempotencyKey) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);

        return idempotencyService.execute(user.userId(), OP_CONVERT + ':' + sessionId, idempotencyKey,
                Map.of("sessionId", sessionId, "ticketId", ticketId), ConsultationProjection.class, () -> {
                    Consultation current = transitionService.load(sessionId);
                    LocalDateTime now = Times.nowUtc();
                    Consultation after = transitionService.apply(current, TransitionSpec.builder()
                            .event(ConsultationEvent.CONSULTATION_CONVERT)
                            .actor(user)
                            .reason("咨询转正式工单 " + ticketId)
                            .setConvertedTicketId(true)
                            .convertedTicketId(ticketId)
                            .setClosedAt(true)
                            .closedAt(now)
                            .eventPayload(Map.of("session_id", sessionId, "ticket_id", ticketId))
                            .build());
                    endActiveAssignment(sessionId);
                    slaService.cancel(sessionId);
                    return ConsultationProjection.of(after);
                }).value();
    }

    private void endActiveAssignment(String sessionId) {
        assignmentService.activeAssignment(sessionId).ifPresent(assignment ->
                assignmentService.endAssignment(assignment.getAssignmentId(),
                        com.itticket.consultation.enums.AssignmentEndReason.CANCELLED, null));
    }

    // ---------------------------------------------------------------- 读取

    /**
     * 返回当前员工已分配工程师的排队人数。人数只统计同一工程师名下仍等待首次回复的咨询，
     * 并包含当前会话自己；尚未分配工程师时不暴露虚构的队列人数。
     */
    public QueueStatusResponse queueStatus(CurrentUser user, String sessionId) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);

        String engineerId = consultation.getCurrentEngineerId();
        if (engineerId == null || engineerId.isBlank()
                || consultation.getStatus() != ConsultationStatus.WAITING_ENGINEER) {
            return new QueueStatusResponse(false, 0);
        }

        long count = consultationMapper.selectCount(Wrappers.<Consultation>lambdaQuery()
                .eq(Consultation::getCurrentEngineerId, engineerId)
                .eq(Consultation::getStatus, ConsultationStatus.WAITING_ENGINEER));
        return new QueueStatusResponse(true, Math.toIntExact(count));
    }

    public Consultation loadAuthorized(CurrentUser user, String sessionId) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireReadBasic(user, consultation);
        return consultation;
    }

    /**
     * OpenAPI 05 getTicketDraftFromConsultation:咨询转单预填。
     *
     * <p>仅会话创建者可取(AX-006:own consultation 的 CREATE_TICKET)。标题取员工首条
     * 实际消息,描述与会话摘要由完整时间线生成(PRD 9.1 第 3 条:可预填标题、分类、
     * 描述、附件及会话摘要,但不得静默代替员工提交——本接口只读,不创建任何工单)。
     */
    public TicketDraftResponse ticketDraft(CurrentUser user, String sessionId) {
        Consultation consultation = transitionService.load(sessionId);
        authzService.requireCreator(user, consultation);

        List<ConsultationMessage> timeline = messageService.loadTimeline(sessionId);
        String title = timeline.stream()
                .filter(m -> m.getSenderType() == MessageSenderType.EMPLOYEE)
                .map(m -> m.getContent() == null ? "" : m.getContent().trim())
                .filter(c -> !c.isEmpty())
                .flatMap(c -> c.lines())
                .filter(l -> !l.isBlank())
                .findFirst().orElse("");
        if (title.length() > 100) {
            title = title.substring(0, 100);
        }

        return new TicketDraftResponse(
                consultation.getSessionId(),
                consultation.getStatus().getValue(),
                consultation.getCategoryId(),
                !consultation.getStatus().isTerminal(),
                title,
                buildTimelineSummary(timeline, 4500),
                buildTimelineSummary(timeline, 2000));
    }

    /** 会话摘要:非系统消息按「角色:内容」逐行拼接,超长截断。 */
    private String buildTimelineSummary(List<ConsultationMessage> timeline, int maxChars) {
        StringBuilder sb = new StringBuilder();
        for (ConsultationMessage m : timeline) {
            if (m.getSenderType() == MessageSenderType.SYSTEM
                    || m.getContent() == null || m.getContent().isBlank()) {
                continue;
            }
            String line = SUMMARY_SENDER.get(m.getSenderType()) + "：" + m.getContent().trim().replaceAll("\\s+", " ");
            if (sb.length() > 0) {
                sb.append('\n');
            }
            if (sb.length() + line.length() > maxChars) {
                sb.append('…');
                break;
            }
            sb.append(line);
        }
        return sb.toString();
    }

    private static final Map<MessageSenderType, String> SUMMARY_SENDER = Map.of(
            MessageSenderType.EMPLOYEE, "员工",
            MessageSenderType.AI, "AI",
            MessageSenderType.ENGINEER, "工程师");

    /**
     * 列表(OpenAPI 05 listConsultations)。
     * 数据范围按 PRD 5.2:员工只看本人,工程师只看当前负责,平台管理员可看全部业务字段。
     */
    public PagedData<ConsultationProjection> list(CurrentUser user, int page, int pageSize) {
        LambdaQueryWrapper<Consultation> query = Wrappers.<Consultation>lambdaQuery();
        if (user.isPlatformAdmin()) {
            // 不加归属条件
        } else if (user.isEngineer()) {
            query.eq(Consultation::getCurrentEngineerId, user.userId());
        } else if (user.isEmployee()) {
            query.eq(Consultation::getCreatorId, user.userId());
        } else {
            throw new ApiException(ApiCode.FORBIDDEN, "当前角色无咨询查询权限");
        }
        query.orderByDesc(Consultation::getCreatedAt).orderByDesc(Consultation::getSessionId);

        IPage<Consultation> result = consultationMapper.selectPage(new Page<>(page, pageSize), query);
        List<ConsultationProjection> items = result.getRecords().stream()
                .map(ConsultationProjection::of)
                .toList();
        return new PagedData<>(items, page, pageSize, result.getTotal());
    }
}
