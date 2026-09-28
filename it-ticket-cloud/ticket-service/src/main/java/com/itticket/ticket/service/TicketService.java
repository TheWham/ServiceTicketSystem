package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.user.UserInfo;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.AcceptRequest;
import com.itticket.ticket.dto.ActionRequest;
import com.itticket.ticket.dto.AssignRequest;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.dto.RatingRequest;
import com.itticket.ticket.entity.Attachment;
import com.itticket.ticket.entity.Category;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketNature;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.IdsRequest;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.AttachmentMapper;
import com.itticket.ticket.mapper.CategoryMapper;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import com.itticket.ticket.statemachine.TicketStateMachine;
import com.itticket.ticket.vo.FlowLogVO;
import com.itticket.ticket.vo.TicketListVO;
import com.itticket.ticket.vo.TicketVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 工单业务 —— 逐方法移植旧版 ticketController.js,错误码/消息/HTTP 语义保持一致。
 * 事务内:更新工单 + 写流转日志;通知一律在事务提交后异步发送。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TicketService {

    private final TicketMapper ticketMapper;
    private final CategoryMapper categoryMapper;
    private final AttachmentMapper attachmentMapper;
    private final TicketFlowLogMapper flowLogMapper;
    private final TicketNoGenerator noGenerator;
    private final NotificationService notificationService;
    private final UserClient userClient;
    private final SlaService slaService;
    private final RoutingService routingService;
    private final ExceptionQueueService exceptionQueueService;

    // ---------------- 创建工单 ----------------

    public record CreateOutcome(boolean duplicated, String ticketId, String title) {
    }

    @Transactional
    public CreateOutcome create(UserContext.CurrentUser creator, CreateTicketRequest req) {
        // 参数校验（PRD §10.2 固定字段）
        List<String> errors = new ArrayList<>();
        if (!TicketNature.isValid(req.getNature())) errors.add("工单性质无效（INCIDENT/SERVICE_REQUEST）");
        if (req.getTitle() == null || req.getTitle().trim().isEmpty()) errors.add("工单标题不能为空");
        if (req.getTitle() != null && req.getTitle().trim().length() > 100) errors.add("工单标题不能超过100字符");
        if (req.getDescription() == null || req.getDescription().trim().length() < 10) errors.add("问题描述至少10个字符");
        if (req.getDescription() != null && req.getDescription().trim().length() > 5000) errors.add("问题描述不能超过5000字符");
        if (req.getImpactDescription() == null || req.getImpactDescription().trim().isEmpty()) errors.add("影响情况不能为空");
        if (req.getUrgencyDescription() == null || req.getUrgencyDescription().trim().isEmpty()) errors.add("紧急说明不能为空");
        if (req.getAttachments() != null && req.getAttachments().size() > 3) errors.add("附件最多3个");

        // 分类必须为启用的末级分类（§10.2）
        Category category = null;
        if (req.getCategoryId() == null || req.getCategoryId().isBlank()) {
            errors.add("分类不能为空");
        } else {
            category = categoryMapper.selectById(req.getCategoryId());
            if (category == null) {
                errors.add("分类不存在");
            } else if (!"ACTIVE".equals(category.getStatus())) {
                errors.add("分类已停用");
            } else if (!isLeafCategory(category)) {
                errors.add("必须选择末级分类");
            }
        }
        if (!errors.isEmpty()) {
            throw new BizException(ErrorCode.PARAM_INVALID, String.join("；", errors));
        }

        // 幂等检查（§10.4 idempotency_key + creator_id）
        if (req.getIdempotencyKey() != null && !req.getIdempotencyKey().isBlank()) {
            Ticket existing = selectByIdempotencyKey(creator.getUserId(), req.getIdempotencyKey());
            if (existing != null) {
                return new CreateOutcome(true, existing.getTicketId(), existing.getTitle());
            }
        }

        // 生成工单号并插入：撞号重试（最多 5 次）
        String ticketId = null;
        for (int attempt = 0; attempt < 5; attempt++) {
            String candidate = noGenerator.generate();
            try {
                ticketId = candidate;
                insertTicket(candidate, req, category, creator);
                break;
            } catch (DuplicateKeyException e) {
                if (attempt == 4) throw e;
                Ticket byKey = req.getIdempotencyKey() == null ? null
                        : selectByIdempotencyKey(creator.getUserId(), req.getIdempotencyKey());
                if (byKey != null) {
                    return new CreateOutcome(true, byKey.getTicketId(), byKey.getTitle());
                }
            }
        }

        String finalTicketId = ticketId;
        insertFlowLog(finalTicketId, null, TicketStatus.NEW.getValue(), creator.getUserId(), "提交工单");

        // 异步通知 + SLA 起算 + 自动路由（事务提交后）
        afterCommit(() -> notificationService.sendNotification(finalTicketId, "SUBMIT_SUCCESS", creator.getUserId()));
        afterCommit(() -> afterCreate(finalTicketId));

        return new CreateOutcome(false, finalTicketId, req.getTitle().trim());
    }

    /** 是否末级分类：没有 ACTIVE 子分类即为末级 */
    private boolean isLeafCategory(Category category) {
        Long children = categoryMapper.selectCount(new QueryWrapper<Category>()
                .eq("parent_id", category.getCategoryId()).eq("status", "ACTIVE"));
        return children == null || children == 0;
    }

    private void insertTicket(String ticketId, CreateTicketRequest req, Category category, UserContext.CurrentUser creator) {
        Ticket ticket = new Ticket();
        ticket.setTicketId(ticketId);
        ticket.setCreatorId(creator.getUserId());
        ticket.setNature(req.getNature());
        ticket.setCategoryId(category.getCategoryId());
        ticket.setCategorySnapshot(buildCategorySnapshot(category));
        ticket.setTitle(req.getTitle().trim());
        ticket.setDescription(req.getDescription().trim());
        ticket.setImpactDescription(req.getImpactDescription().trim());
        ticket.setUrgencyDescription(req.getUrgencyDescription().trim());
        ticket.setLocation(req.getLocation());
        ticket.setContact(req.getContact());
        ticket.setAssetId(req.getAssetId());
        ticket.setAssetCheckStatus(req.getAssetId() == null ? null : "PENDING");
        ticket.setStatus(TicketStatus.NEW);
        // 新单暂按中优先级计时（§11.4），接单时按矩阵确认正式优先级
        ticket.setPriority(PriorityMatrix.MEDIUM);
        ticket.setAssigneeId(null);
        ticket.setSourceSessionId(req.getSourceSessionId());
        ticket.setAutoAccepted(0);
        ticket.setReopenCount(0);
        ticket.setIdempotencyKey(req.getIdempotencyKey());
        ticket.setVersion(0);
        ticket.setFirstResponseAt(null);
        ticket.setCreatedAt(LocalDateTime.now());
        ticket.setUpdatedAt(LocalDateTime.now());
        ticketMapper.insert(ticket);
    }

    /** 分类快照：停用后仍可读（§10.1），格式 一级/二级/三级 */
    private String buildCategorySnapshot(Category leaf) {
        List<String> names = new ArrayList<>();
        Category cur = leaf;
        int guard = 0;
        while (cur != null && guard++ < 5) {
            names.add(0, cur.getName());
            cur = cur.getParentId() == null ? null : categoryMapper.selectById(cur.getParentId());
        }
        return String.join("/", names);
    }

    // ---------------- 工单列表 ----------------

    public TicketListVO list(String status, String categoryId, String assigneeId, String creatorId,
                             String priority, String unassigned, String mineOrPool, int page, int pageSize) {
        QueryWrapper<Ticket> qw = new QueryWrapper<>();
        if (status != null && !status.isBlank()) qw.eq("status", status);
        if (categoryId != null && !categoryId.isBlank()) qw.eq("category_id", categoryId);
        if (assigneeId != null && !assigneeId.isBlank()) qw.eq("assignee_id", assigneeId);
        if (creatorId != null && !creatorId.isBlank()) qw.eq("creator_id", creatorId);
        if (priority != null && !priority.isBlank()) qw.eq("priority", priority);
        // 待领取池:尚未派单的「待处理」工单
        if ("true".equals(unassigned) || "1".equals(unassigned)) {
            qw.isNull("assignee_id").eq("status", TicketStatus.NEW.getValue());
        }
        // 工程师看板:我负责的工单 + 尚无人认领的待处理工单
        if (mineOrPool != null && !mineOrPool.isBlank()) {
            qw.and(w -> w.eq("assignee_id", mineOrPool)
                    .or(o -> o.isNull("assignee_id").eq("status", TicketStatus.NEW.getValue())));
        }
        qw.orderByDesc("created_at").orderByDesc("ticket_id");

        Page<Ticket> result = ticketMapper.selectPage(new Page<>(page, pageSize), qw);
        Map<String, UserInfo> users = batchUsers(collectUserIds(result.getRecords()));

        List<TicketVO> list = result.getRecords().stream().map(t -> {
            TicketVO vo = TicketVO.from(t);
            vo.setAttachments(listAttachmentIds(t.getTicketId()));
            UserInfo creator = users.get(t.getCreatorId());
            UserInfo assignee = t.getAssigneeId() == null ? null : users.get(t.getAssigneeId());
            vo.setCreatorName(creator == null ? null : creator.getName());
            vo.setAssigneeName(assignee == null ? null : assignee.getName());
            return vo;
        }).toList();
        return new TicketListVO(list, result.getTotal(), page, pageSize);
    }

    // ---------------- 工单详情 ----------------

    public Map<String, Object> get(String ticketId) {
        Ticket ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) {
            throw new BizException(ErrorCode.TICKET_NOT_FOUND);
        }
        List<TicketFlowLog> flows = flowLogMapper.selectList(new QueryWrapper<TicketFlowLog>()
                .eq("ticket_id", ticketId)
                .orderByAsc("occurred_at").orderByAsc("transition_id"));

        LinkedHashSet<String> userIds = new LinkedHashSet<>();
        userIds.add(ticket.getCreatorId());
        if (ticket.getAssigneeId() != null) userIds.add(ticket.getAssigneeId());
        flows.forEach(f -> userIds.add(f.getOperatorId()));
        Map<String, UserInfo> users = batchUsers(userIds);

        TicketVO vo = TicketVO.from(ticket);
        vo.setAttachments(listAttachmentIds(ticketId));
        UserInfo creator = users.get(ticket.getCreatorId());
        UserInfo assignee = ticket.getAssigneeId() == null ? null : users.get(ticket.getAssigneeId());
        vo.setCreatorName(creator == null ? null : creator.getName());
        vo.setAssigneeName(assignee == null ? null : assignee.getName());

        List<FlowLogVO> flowVos = flows.stream().map(f -> {
            FlowLogVO fvo = FlowLogVO.from(f);
            UserInfo operator = users.get(f.getOperatorId());
            fvo.setOperatorName(operator == null ? null : operator.getName());
            return fvo;
        }).toList();

        return Map.of("ticket", vo, "flow_logs", flowVos);
    }

    // ---------------- 派单 / 改派(仅主管) ----------------

    public record AssignOutcome(boolean reassign, String ticketId, String assigneeId) {
    }

    @Transactional
    public AssignOutcome assign(UserContext.CurrentUser operator, String ticketId, AssignRequest req) {
        UserContext.checkRole(operator, "PLATFORM_ADMIN");
        if (req.getAssigneeId() == null || req.getAssigneeId().isBlank()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请选择处理人");
        }

        // 校验处理人(经 Feign 调 user-service,对应旧版同库查询)
        UserInfo assignee;
        try {
            assignee = userClient.getUser(req.getAssigneeId()).getData();
        } catch (Exception e) {
            log.error("[TICKET] 校验处理人失败: {}", e.getMessage());
            throw new BizException(ErrorCode.SYSTEM_ERROR, "用户服务暂不可用");
        }
        if (assignee == null || !"ENGINEER".equals(assignee.getRole()) || !"ACTIVE".equals(assignee.getStatus())) {
            throw new BizException(ErrorCode.ASSIGNEE_INVALID);
        }

        Ticket ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) throw new BizException(ErrorCode.TICKET_NOT_FOUND);

        // 改派为主管干预操作：仅终态（已完成/已取消/已关闭）不可改派，其余状态允许
        if (TicketStatus.COMPLETED == ticket.getStatus()
                || TicketStatus.CANCELLED == ticket.getStatus()
                || TicketStatus.CLOSED == ticket.getStatus()) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, "终态工单不可改派");
        }

        String oldAssignee = ticket.getAssigneeId();
        boolean isReassign = oldAssignee != null && !oldAssignee.equals(req.getAssigneeId());

        // 写 assignment 分配记录（转派不删历史责任 §12.3）
        routingService.assign(ticket, req.getAssigneeId(), isReassign ? "TRANSFER_APPLY" : null);

        ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
                .eq(Ticket::getTicketId, ticketId)
                .set(Ticket::getStatus, TicketStatus.ASSIGNED)
                .set(Ticket::getUpdatedAt, LocalDateTime.now()));
        insertFlowLog(ticketId, ticket.getStatus().getValue(), TicketStatus.ASSIGNED.getValue(),
                operator.getUserId(), (isReassign ? "改派: " : "派单: ") + (req.getReason() == null || req.getReason().isBlank() ? "无" : req.getReason()));

        afterCommit(() -> notificationService.sendNotification(ticketId, "ASSIGNED", req.getAssigneeId()));

        return new AssignOutcome(isReassign, ticketId, req.getAssigneeId());
    }

    // ---------------- 领取(仅工程师) ----------------

    @Transactional
    public Map<String, Object> claim(UserContext.CurrentUser operator, String ticketId, AcceptRequest req) {
        UserContext.checkRole(operator, "ENGINEER");

        Ticket ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) throw new BizException(ErrorCode.TICKET_NOT_FOUND);

        // 接单必须确认影响范围与紧急程度，按 §11.4 矩阵算正式优先级（工程师不能绕过矩阵指定结果）
        String priority = PriorityMatrix.compute(req.getImpactScope(), req.getUrgencyLevel());
        if (priority == null) {
            throw new BizException(ErrorCode.PARAM_INVALID,
                    "影响范围(SINGLE/DEPARTMENT/CROSS_DEPT)或紧急程度(LOW/MEDIUM/HIGH)无效");
        }

        // 状态机校验(accept 接单仅限 engineer;支持 ASSIGNED→IN_PROGRESS)
        TicketStateMachine.ValidationResult validation =
                TicketStateMachine.validateTransition(ticket.getStatus(), TicketStatus.IN_PROGRESS, operator.getRole(), "accept");
        if (!validation.isValid()) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, validation.getMsg());
        }

        String oldPriority = ticket.getPriority();
        // 条件更新:仅当工单当前分配给本人时才成功(防止越权接单);同时写入矩阵结果
        int rows = ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
                .eq(Ticket::getTicketId, ticketId)
                .eq(Ticket::getAssigneeId, operator.getUserId())
                .eq(Ticket::getStatus, TicketStatus.ASSIGNED)
                .set(Ticket::getStatus, TicketStatus.IN_PROGRESS)
                .set(Ticket::getPriority, priority)
                .set(Ticket::getImpactScope, req.getImpactScope())
                .set(Ticket::getUrgencyLevel, req.getUrgencyLevel())
                .setSql("first_response_at = COALESCE(first_response_at, NOW())"));
        if (rows == 0) {
            throw new BizException(ErrorCode.NOT_CLAIMABLE, "工单未分配给你或已被处理");
        }

        // 标记工程师首次响应（§12.2 响应 SLA）
        routingService.markResponded(ticketId, operator.getUserId());

        // 优先级变化：重算完成 SLA 目标（§11.4 优先级变化后重新计算完成目标）
        if (!priority.equals(oldPriority)) {
            slaService.onPriorityChanged(ticketId, priority);
        }

        insertFlowLog(ticketId, ticket.getStatus().getValue(), TicketStatus.IN_PROGRESS.getValue(),
                operator.getUserId(), "工程师接单，确认影响=" + req.getImpactScope() + " 紧急=" + req.getUrgencyLevel()
                        + "，优先级 " + oldPriority + "→" + priority);

        afterCommit(() -> notificationService.sendNotification(ticketId, "ACCEPTED", ticket.getCreatorId()));

        return Map.of("ticket_id", ticketId, "status", TicketStatus.IN_PROGRESS.getValue(),
                "assignee_id", operator.getUserId(), "priority", priority);
    }

    // ---------------- 通用状态操作 ----------------

    private record ActionSpec(TicketStatus to, List<TicketStatus> froms) {
    }

    private static final Map<String, ActionSpec> ACTION_MAP = Map.of(
            "progress", new ActionSpec(TicketStatus.IN_PROGRESS, List.of(TicketStatus.PENDING_SUPPLEMENT, TicketStatus.PENDING_EXTERNAL, TicketStatus.IN_PROGRESS)),
            "need_info", new ActionSpec(TicketStatus.PENDING_SUPPLEMENT, List.of(TicketStatus.IN_PROGRESS)),
            "external", new ActionSpec(TicketStatus.PENDING_EXTERNAL, List.of(TicketStatus.IN_PROGRESS)),
            "done", new ActionSpec(TicketStatus.PENDING_ACCEPTANCE, List.of(TicketStatus.IN_PROGRESS)),
            "accept", new ActionSpec(TicketStatus.COMPLETED, List.of(TicketStatus.PENDING_ACCEPTANCE)),
            "reject", new ActionSpec(TicketStatus.IN_PROGRESS, List.of(TicketStatus.PENDING_ACCEPTANCE)),
            "cancel", new ActionSpec(TicketStatus.CANCELLED, List.of(TicketStatus.NEW)),
            "supply_info", new ActionSpec(TicketStatus.IN_PROGRESS, List.of(TicketStatus.PENDING_SUPPLEMENT)),
            "external_resolved", new ActionSpec(TicketStatus.IN_PROGRESS, List.of(TicketStatus.PENDING_EXTERNAL))
    );

    /** 前端动作名 → 状态机边 action 名（用于 getEventType，保持前端契约不变） */
    private static final Map<String, String> EVENT_ACTION_MAP = Map.of(
            "need_info", "request_supplement",
            "external", "external_wait",
            "done", "submit_resolution",
            "accept", "accept",
            "reject", "reject",
            "cancel", "cancel",
            "supply_info", "supply_info",
            "external_resolved", "external_resolved"
    );

    @Transactional
    public Map<String, Object> action(UserContext.CurrentUser operator, String ticketId, ActionRequest req) {
        Ticket ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) throw new BizException(ErrorCode.TICKET_NOT_FOUND);

        ActionSpec mapping = req.getAction() == null ? null : ACTION_MAP.get(req.getAction());
        if (mapping == null) {
            throw new BizException(ErrorCode.PARAM_INVALID, "未知操作: " + req.getAction());
        }
        if (!mapping.froms().contains(ticket.getStatus())) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                    "当前状态「" + ticket.getStatus().getValue() + "」不允许「" + req.getAction() + "」操作");
        }

        // 特定操作校验(与旧版一致)
        if ("done".equals(req.getAction()) && req.getRemark() != null && req.getRemark().length() < 5) {
            throw new BizException(ErrorCode.PARAM_INVALID, "处理说明至少5个字符");
        }
        if ("reject".equals(req.getAction()) && (req.getRemark() == null || req.getRemark().length() < 10)) {
            throw new BizException(ErrorCode.PARAM_INVALID, "驳回原因至少10个字符");
        }
        if ("external".equals(req.getAction()) && (req.getRemark() == null || req.getRemark().length() < 10)) {
            throw new BizException(ErrorCode.PARAM_INVALID, "外部依赖说明至少10个字符");
        }

        // 工程师完成前至少有一条进展记录
        if ("done".equals(req.getAction()) && "ENGINEER".equals(operator.getRole())) {
            Long cnt = flowLogMapper.selectCount(new QueryWrapper<TicketFlowLog>()
                    .eq("ticket_id", ticketId)
                    .eq("operator_id", operator.getUserId())
                    .ne("reason", "提交工单"));
            if (cnt == null || cnt == 0) {
                throw new BizException(ErrorCode.PARAM_INVALID, "请至少记录一条处理进展后再提交");
            }
        }

        // 补充信息守卫（§9.4）：同一工单累计请求补充达 3 次，第 4 次起禁止再发起，必须走关闭/升级异常
        if ("need_info".equals(req.getAction())) {
            Long supplementCount = flowLogMapper.selectCount(new QueryWrapper<TicketFlowLog>()
                    .eq("ticket_id", ticketId)
                    .eq("to_status", TicketStatus.PENDING_SUPPLEMENT.getValue()));
            if (supplementCount != null && supplementCount >= 3) {
                // 已发起 3 次请求补充：转入异常队列，禁止无限循环
                exceptionQueueService.raise("TICKET", ticketId,
                        ExceptionQueueService.TYPE_LIMIT_EXCEEDED,
                        "请求补充次数超限", "累计请求补充已达 3 次仍未闭环，请人工介入（关闭或升级处理）",
                        ticket.getPriority());
                throw new BizException(ErrorCode.ILLEGAL_TRANSITION,
                        "本工单已累计请求补充 3 次，不允许再次发起；请选择关闭工单或升级异常处理");
            }
        }

        LambdaUpdateWrapper<Ticket> uw = new LambdaUpdateWrapper<Ticket>()
                .eq(Ticket::getTicketId, ticketId)
                .set(Ticket::getStatus, mapping.to());
        if ("done".equals(req.getAction()) || "accept".equals(req.getAction()) || "cancel".equals(req.getAction())) {
            uw.set(Ticket::getSolvedAt, LocalDateTime.now());
        }
        // 取消时清除处理人
        if ("cancel".equals(req.getAction())) {
            uw.set(Ticket::getAssigneeId, null);
        }
        ticketMapper.update(null, uw);

        // SLA 联动（F-08，§11.3/§11.4）
        applySlaOnTransition(ticketId, req.getAction(), mapping.to(), operator.getUserId());

        String flowRemark = (req.getRemark() != null && !req.getRemark().isEmpty()) ? req.getRemark() : mapping.to().getValue();
        insertFlowLog(ticketId, ticket.getStatus().getValue(), mapping.to().getValue(), operator.getUserId(), flowRemark);

        // 通知(接收人按「更新后」的工单计算,与旧版 {...ticket, ...updateFields} 一致)
        Ticket updated = copyOf(ticket);
        updated.setStatus(mapping.to());
        if ("cancel".equals(req.getAction())) updated.setAssigneeId(null);
        String eventAction = EVENT_ACTION_MAP.getOrDefault(req.getAction(), req.getAction());
        String eventType = TicketStateMachine.getEventType(eventAction);
        List<String> receivers = TicketStateMachine.getNotifyReceivers(updated, mapping.to());
        afterCommit(() -> receivers.forEach(r -> notificationService.sendNotification(ticketId, eventType, r)));

        return Map.of("ticket_id", ticketId, "status", mapping.to().getValue());
    }

    // ---------------- 满意度评价 ----------------

    public void rate(String ticketId, RatingRequest req) {
        if (req.getScore() == null || req.getScore() < 1 || req.getScore() > 5) {
            throw new BizException(ErrorCode.PARAM_INVALID, "评分须为 1-5");
        }
        if (req.getComment() != null && req.getComment().length() > 200) {
            throw new BizException(ErrorCode.PARAM_INVALID, "评语不超过200字");
        }
        Ticket ticket = ticketMapper.selectOne(new QueryWrapper<Ticket>()
                .eq("ticket_id", ticketId)
                .eq("status", TicketStatus.COMPLETED.getValue()));
        if (ticket == null) {
            throw new BizException(ErrorCode.PARAM_INVALID, "仅已完成的工单可评价");
        }
        Ticket update = new Ticket();
        update.setTicketId(ticketId);
        update.setRatingScore(req.getScore());
        update.setRatingComment(req.getComment());
        update.setRatedAt(LocalDateTime.now());
        ticketMapper.updateById(update);
    }

    // ---------------- 私有工具 ----------------

    /**
     * SLA 联动（F-08）：按流转动作暂停/恢复/停止完成 SLA。
     * need_info / external  → 暂停（§11.3）
     * supply_info / external_resolved / progress → 恢复（§11.3）
     * done / accept / cancel → 停止（§11.4 验收阶段不消耗）
     * progress → 同时标记工程师首次响应（§12.2 响应 SLA）
     */
    private void applySlaOnTransition(String ticketId, String action, TicketStatus toStatus, String operatorId) {
        try {
            switch (action) {
                case "need_info" -> slaService.pause(ticketId, "SUPPLEMENT", operatorId);
                case "external" -> slaService.pause(ticketId, "EXTERNAL", operatorId);
                case "supply_info", "external_resolved" -> slaService.resume(ticketId, operatorId);
                case "progress" -> {
                    slaService.resume(ticketId, operatorId);
                    routingService.markResponded(ticketId, operatorId);
                }
                case "done", "accept", "cancel" -> slaService.stop(ticketId);
                default -> { /* 其他流转不动 SLA */ }
            }
        } catch (Exception e) {
            // SLA 联动失败不阻塞主流程
            log.error("[SLA] 联动处理失败: " + ticketId + " action=" + action, e);
        }
    }

    /** 按幂等键 + 创建人查重（§10.4：同一创建人同一 idempotency_key 只建一单） */
    private Ticket selectByIdempotencyKey(String creatorId, String idempotencyKey) {
        return ticketMapper.selectOne(new QueryWrapper<Ticket>()
                .eq("creator_id", creatorId).eq("idempotency_key", idempotencyKey));
    }

    private void insertFlowLog(String ticketId, String fromStatus, String toStatus, String operatorId, String remark) {
        TicketFlowLog flow = new TicketFlowLog();
        flow.setTicketId(ticketId);
        flow.setFromStatus(fromStatus);
        flow.setToStatus(toStatus);
        flow.setEvent(toStatus != null ? toStatus.toLowerCase() : null);
        flow.setOperatorId(operatorId);
        flow.setReason(remark);
        flow.setOccurredAt(LocalDateTime.now());
        flowLogMapper.insert(flow);
    }

    /**
     * 创建后后处理（事务提交后异步）：SLA 起算（§11.2）+ 自动路由（F-06）。
     * 路由成功：NEW → ASSIGNED，并通知工程师（§14.2）。
     * 路由失败：RoutingService 已落异常队列，工单保持 NEW 待管理员处理。
     */
    private void afterCreate(String ticketId) {
        try {
            Ticket ticket = ticketMapper.selectById(ticketId);
            if (ticket == null || ticket.getStatus() != TicketStatus.NEW) {
                return;
            }
            // 1. SLA 起算（完成 SLA 创建起算，新单默认 MEDIUM）
            slaService.startCompletionSla(ticketId, ticket.getPriority(), LocalDateTime.now());

            // 2. 自动路由
            String engineerId = routingService.route(ticket);
            if (engineerId == null) {
                return; // 路由失败已入异常队列
            }
            // NEW → ASSIGNED
            ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
                    .eq(Ticket::getTicketId, ticketId)
                    .eq(Ticket::getStatus, TicketStatus.NEW)
                    .set(Ticket::getStatus, TicketStatus.ASSIGNED)
                    .set(Ticket::getUpdatedAt, LocalDateTime.now()));
            insertFlowLog(ticketId, TicketStatus.NEW.getValue(), TicketStatus.ASSIGNED.getValue(),
                    "SYSTEM", "自动路由分配: " + engineerId);
            notificationService.sendNotification(ticketId, "ASSIGNED", engineerId);
        } catch (Exception e) {
            log.error("[TICKET] 创建后处理失败: " + ticketId, e);
        }
    }

    private Collection<String> collectUserIds(List<Ticket> tickets) {
        LinkedHashSet<String> ids = new LinkedHashSet<>();
        for (Ticket t : tickets) {
            ids.add(t.getCreatorId());
            if (t.getAssigneeId() != null) ids.add(t.getAssigneeId());
        }
        return ids;
    }

    /** 批量查用户姓名;失败降级为空 Map(等价旧版 LEFT JOIN 查不到置 null,不阻塞列表) */
    private Map<String, UserInfo> batchUsers(Collection<String> ids) {
        if (ids == null || ids.isEmpty()) return Map.of();
        try {
            var res = userClient.batch(new IdsRequest(new ArrayList<>(ids)));
            if (res == null || res.getData() == null) return Map.of();
            return res.getData().stream().collect(Collectors.toMap(UserInfo::getUserId, u -> u, (a, b) -> a));
        } catch (Exception e) {
            log.warn("[TICKET] 批量查询用户失败(姓名置空): {}", e.getMessage());
            return Map.of();
        }
    }

    private void afterCommit(Runnable task) {
        if (TransactionSynchronizationManager.isSynchronizationActive()) {
            TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                @Override
                public void afterCommit() {
                    task.run();
                }
            });
        } else {
            task.run();
        }
    }

    /** 查工单的可用附件 id 列表（attachment 表，仅 CLEAN 未撤回） */
    private List<String> listAttachmentIds(String ticketId) {
        List<Attachment> atts = attachmentMapper.selectList(new QueryWrapper<Attachment>()
                .eq("biz_type", "TICKET").eq("biz_id", ticketId)
                .eq("scan_status", "CLEAN").isNull("withdrawn_at"));
        if (atts == null || atts.isEmpty()) return List.of();
        return atts.stream().map(Attachment::getAttachmentId).toList();
    }

    private Ticket copyOf(Ticket t) {
        Ticket c = new Ticket();
        c.setTicketId(t.getTicketId());
        c.setCreatorId(t.getCreatorId());
        c.setAssigneeId(t.getAssigneeId());
        c.setStatus(t.getStatus());
        return c;
    }
}
