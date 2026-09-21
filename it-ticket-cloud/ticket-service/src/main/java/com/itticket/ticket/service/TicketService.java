package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.user.UserInfo;
import com.itticket.common.web.UserContext;
import com.itticket.ticket.dto.ActionRequest;
import com.itticket.ticket.dto.AssignRequest;
import com.itticket.ticket.dto.CreateTicketRequest;
import com.itticket.ticket.dto.RatingRequest;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.IdsRequest;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import com.itticket.ticket.statemachine.TicketStateMachine;
import com.itticket.ticket.vo.FlowLogVO;
import com.itticket.ticket.vo.TicketListVO;
import com.itticket.ticket.vo.TicketVO;
import com.fasterxml.jackson.databind.ObjectMapper;
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

    private static final List<String> CATEGORIES = List.of("硬件", "软件", "网络", "账号", "其他");
    private static final List<String> PRIORITIES = List.of("高", "中", "低");

    private final TicketMapper ticketMapper;
    private final TicketFlowLogMapper flowLogMapper;
    private final TicketNoGenerator noGenerator;
    private final NotificationService notificationService;
    private final UserClient userClient;
    private final ObjectMapper objectMapper;

    // ---------------- 创建工单 ----------------

    public record CreateOutcome(boolean duplicated, String ticketId, String title) {
    }

    @Transactional
    public CreateOutcome create(UserContext.CurrentUser creator, CreateTicketRequest req) {
        // 参数校验(与旧版逐字一致,错误用全角分号连接)
        List<String> errors = new ArrayList<>();
        String finalTitle = firstNonBlank(req.getTitle()) != null
                ? req.getTitle().trim()
                : (req.getDescription() != null && req.getDescription().trim().length() > 0
                        ? truncate(req.getDescription().trim(), 50) : "");
        if (finalTitle.isEmpty()) errors.add("工单标题不能为空");
        if (finalTitle.length() > 50) errors.add("工单标题不能超过50个字符");
        if (req.getCategory() == null || !CATEGORIES.contains(req.getCategory())) errors.add("问题分类无效");
        if (req.getDescription() == null || req.getDescription().trim().length() < 10) errors.add("问题描述至少10个字符");
        if (req.getDescription() != null && req.getDescription().trim().length() > 500) errors.add("问题描述不能超过500字符");
        String priority = req.getPriority() == null ? "中" : req.getPriority();
        if (!PRIORITIES.contains(priority)) errors.add("优先级无效");
        if (req.getAttachmentUrls() != null && req.getAttachmentUrls().size() > 3) errors.add("截图附件最多3张");
        if (req.getExpectedFinishTime() != null && req.getExpectedFinishTime().isBefore(LocalDateTime.now())) {
            errors.add("期望完成时间不能早于当前时间");
        }
        if (!errors.isEmpty()) {
            throw new BizException(ErrorCode.PARAM_INVALID, String.join("；", errors));
        }

        // 幂等检查
        if (req.getClientToken() != null && !req.getClientToken().isBlank()) {
            Ticket existing = selectByClientToken(req.getClientToken());
            if (existing != null) {
                return new CreateOutcome(true, existing.getTicketId(), finalTitle);
            }
        }

        // 生成工单号并插入:并发「查最大号 + 自增」存在撞号可能,命中主键冲突时重试(与旧版一致,最多 5 次)
        String ticketId = null;
        for (int attempt = 0; attempt < 5; attempt++) {
            String candidate = noGenerator.generate();
            try {
                ticketId = candidate;
                insertTicket(candidate, finalTitle, req, priority, creator);
                break;
            } catch (DuplicateKeyException e) {
                if (attempt == 4) throw e;
                Ticket byToken = req.getClientToken() == null ? null : selectByClientToken(req.getClientToken());
                if (byToken != null) {
                    // 并发窗口内同 client_token 已落库 → 幂等返回
                    return new CreateOutcome(true, byToken.getTicketId(), finalTitle);
                }
                // 工单号撞号 → 换号重试
            }
        }

        String finalTicketId = ticketId;
        insertFlowLog(finalTicketId, null, TicketStatus.PENDING.getValue(), creator.getUserId(), "提交工单");

        // 异步通知(事务提交后,不阻塞响应)
        afterCommit(() -> notificationService.sendNotification(finalTicketId, "SUBMIT_SUCCESS", creator.getUserId()));

        return new CreateOutcome(false, finalTicketId, finalTitle);
    }

    private void insertTicket(String ticketId, String title, CreateTicketRequest req, String priority, UserContext.CurrentUser creator) {
        Ticket ticket = new Ticket();
        ticket.setTicketId(ticketId);
        ticket.setTitle(title);
        ticket.setDescription(req.getDescription().trim());
        ticket.setCategory(req.getCategory());
        ticket.setPriority(priority);
        ticket.setStatus(TicketStatus.PENDING);
        ticket.setCreatorId(creator.getUserId());
        ticket.setAssetId(req.getAssetId());
        ticket.setExpectedFinishTime(req.getExpectedFinishTime());
        ticket.setAttachmentUrls(toJson(req.getAttachmentUrls()));
        ticket.setClientToken(req.getClientToken());
        ticket.setFirstResponseAt(LocalDateTime.now());
        ticket.setCreatedAt(LocalDateTime.now());
        ticket.setUpdatedAt(LocalDateTime.now());
        ticketMapper.insert(ticket);
    }

    // ---------------- 工单列表 ----------------

    public TicketListVO list(String status, String category, String assigneeId, String creatorId,
                             String priority, String unassigned, String mineOrPool, int page, int pageSize) {
        QueryWrapper<Ticket> qw = new QueryWrapper<>();
        if (status != null && !status.isBlank()) qw.eq("status", status);
        if (category != null && !category.isBlank()) qw.eq("category", category);
        if (assigneeId != null && !assigneeId.isBlank()) qw.eq("assignee_id", assigneeId);
        if (creatorId != null && !creatorId.isBlank()) qw.eq("creator_id", creatorId);
        if (priority != null && !priority.isBlank()) qw.eq("priority", priority);
        // 待领取池:尚未派单的「待处理」工单
        if ("true".equals(unassigned) || "1".equals(unassigned)) {
            qw.isNull("assignee_id").eq("status", TicketStatus.PENDING.getValue());
        }
        // 工程师看板:我负责的工单 + 尚无人认领的待处理工单
        if (mineOrPool != null && !mineOrPool.isBlank()) {
            qw.and(w -> w.eq("assignee_id", mineOrPool)
                    .or(o -> o.isNull("assignee_id").eq("status", TicketStatus.PENDING.getValue())));
        }
        qw.orderByDesc("created_at").orderByDesc("ticket_id");

        Page<Ticket> result = ticketMapper.selectPage(new Page<>(page, pageSize), qw);
        Map<String, UserInfo> users = batchUsers(collectUserIds(result.getRecords()));

        List<TicketVO> list = result.getRecords().stream().map(t -> {
            TicketVO vo = TicketVO.from(t);
            vo.setAttachmentUrls(parseAttachments(t.getAttachmentUrls()));
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
                .orderByAsc("created_at").orderByAsc("log_id"));

        LinkedHashSet<String> userIds = new LinkedHashSet<>();
        userIds.add(ticket.getCreatorId());
        if (ticket.getAssigneeId() != null) userIds.add(ticket.getAssigneeId());
        flows.forEach(f -> userIds.add(f.getOperatorId()));
        Map<String, UserInfo> users = batchUsers(userIds);

        TicketVO vo = TicketVO.from(ticket);
        vo.setAttachmentUrls(parseAttachments(ticket.getAttachmentUrls()));
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
        UserContext.checkRole(operator, "supervisor");
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
        if (assignee == null || !"engineer".equals(assignee.getRole()) || !"active".equals(assignee.getStatus())) {
            throw new BizException(ErrorCode.ASSIGNEE_INVALID);
        }

        Ticket ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) throw new BizException(ErrorCode.TICKET_NOT_FOUND);

        TicketStateMachine.ValidationResult validation =
                TicketStateMachine.validateTransition(ticket.getStatus(), TicketStatus.PROCESSING, operator.getRole(), "assign");
        if (!validation.isValid()) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, validation.getMsg());
        }

        String oldAssignee = ticket.getAssigneeId();
        boolean isReassign = oldAssignee != null && !oldAssignee.equals(req.getAssigneeId());

        ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
                .eq(Ticket::getTicketId, ticketId)
                .set(Ticket::getAssigneeId, req.getAssigneeId())
                .set(Ticket::getStatus, TicketStatus.PROCESSING)
                .setSql("first_response_at = COALESCE(first_response_at, NOW())"));
        insertFlowLog(ticketId, ticket.getStatus().getValue(), TicketStatus.PROCESSING.getValue(),
                operator.getUserId(), (isReassign ? "改派: " : "派单: ") + (req.getReason() == null || req.getReason().isBlank() ? "无" : req.getReason()));

        afterCommit(() -> notificationService.sendNotification(ticketId, "DISPATCH", req.getAssigneeId()));

        return new AssignOutcome(isReassign, ticketId, req.getAssigneeId());
    }

    // ---------------- 领取(仅工程师) ----------------

    @Transactional
    public Map<String, Object> claim(UserContext.CurrentUser operator, String ticketId) {
        UserContext.checkRole(operator, "engineer");

        Ticket ticket = ticketMapper.selectById(ticketId);
        if (ticket == null) throw new BizException(ErrorCode.TICKET_NOT_FOUND);

        // 状态机校验(claim 转移仅限 engineer)
        TicketStateMachine.ValidationResult validation =
                TicketStateMachine.validateTransition(ticket.getStatus(), TicketStatus.PROCESSING, operator.getRole(), "claim");
        if (!validation.isValid()) {
            throw new BizException(ErrorCode.ILLEGAL_TRANSITION, validation.getMsg());
        }
        if (!"claim".equals(validation.getTransition().action())) {
            throw new BizException(ErrorCode.NOT_CLAIMABLE);
        }

        // 条件更新:仅当工单仍无人认领时才成功(防止两人同时点「领取」)
        int rows = ticketMapper.update(null, new LambdaUpdateWrapper<Ticket>()
                .eq(Ticket::getTicketId, ticketId)
                .isNull(Ticket::getAssigneeId)
                .eq(Ticket::getStatus, TicketStatus.PENDING)
                .set(Ticket::getAssigneeId, operator.getUserId())
                .set(Ticket::getStatus, TicketStatus.PROCESSING)
                .setSql("first_response_at = COALESCE(first_response_at, NOW())"));
        if (rows == 0) {
            throw new BizException(ErrorCode.ALREADY_CLAIMED);
        }

        insertFlowLog(ticketId, ticket.getStatus().getValue(), TicketStatus.PROCESSING.getValue(),
                operator.getUserId(), "工程师领取工单");

        afterCommit(() -> notificationService.sendNotification(ticketId, "DISPATCH", operator.getUserId()));

        return Map.of("ticket_id", ticketId, "status", TicketStatus.PROCESSING.getValue(), "assignee_id", operator.getUserId());
    }

    // ---------------- 通用状态操作 ----------------

    private record ActionSpec(TicketStatus to, List<TicketStatus> froms) {
    }

    private static final Map<String, ActionSpec> ACTION_MAP = Map.of(
            "progress", new ActionSpec(TicketStatus.PROCESSING, List.of(TicketStatus.NEED_INFO, TicketStatus.EXTERNAL, TicketStatus.PROCESSING)),
            "need_info", new ActionSpec(TicketStatus.NEED_INFO, List.of(TicketStatus.PROCESSING)),
            "external", new ActionSpec(TicketStatus.EXTERNAL, List.of(TicketStatus.PROCESSING)),
            "done", new ActionSpec(TicketStatus.ACCEPTANCE, List.of(TicketStatus.PROCESSING)),
            "accept", new ActionSpec(TicketStatus.DONE, List.of(TicketStatus.ACCEPTANCE)),
            "reject", new ActionSpec(TicketStatus.PROCESSING, List.of(TicketStatus.ACCEPTANCE)),
            "cancel", new ActionSpec(TicketStatus.CANCELLED, List.of(TicketStatus.PENDING)),
            "supply_info", new ActionSpec(TicketStatus.PROCESSING, List.of(TicketStatus.NEED_INFO)),
            "external_resolved", new ActionSpec(TicketStatus.PROCESSING, List.of(TicketStatus.EXTERNAL))
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
        if ("done".equals(req.getAction()) && "engineer".equals(operator.getRole())) {
            Long cnt = flowLogMapper.selectCount(new QueryWrapper<TicketFlowLog>()
                    .eq("ticket_id", ticketId)
                    .eq("operator_id", operator.getUserId())
                    .ne("remark", "提交工单"));
            if (cnt == null || cnt == 0) {
                throw new BizException(ErrorCode.PARAM_INVALID, "请至少记录一条处理进展后再提交");
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

        String flowRemark = (req.getRemark() != null && !req.getRemark().isEmpty()) ? req.getRemark() : mapping.to().getValue();
        insertFlowLog(ticketId, ticket.getStatus().getValue(), mapping.to().getValue(), operator.getUserId(), flowRemark);

        // 通知(接收人按「更新后」的工单计算,与旧版 {...ticket, ...updateFields} 一致)
        Ticket updated = copyOf(ticket);
        updated.setStatus(mapping.to());
        if ("cancel".equals(req.getAction())) updated.setAssigneeId(null);
        String eventType = TicketStateMachine.getEventType(req.getAction());
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
                .eq("status", TicketStatus.DONE.getValue()));
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

    private Ticket selectByClientToken(String clientToken) {
        return ticketMapper.selectOne(new QueryWrapper<Ticket>().eq("client_token", clientToken));
    }

    private void insertFlowLog(String ticketId, String fromStatus, String toStatus, String operatorId, String remark) {
        TicketFlowLog flow = new TicketFlowLog();
        flow.setTicketId(ticketId);
        flow.setFromStatus(fromStatus);
        flow.setToStatus(toStatus);
        flow.setOperatorId(operatorId);
        flow.setRemark(remark);
        flow.setCreatedAt(LocalDateTime.now());
        flowLogMapper.insert(flow);
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

    private String firstNonBlank(String s) {
        return (s != null && !s.trim().isEmpty()) ? s.trim() : null;
    }

    private String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max);
    }

    private String toJson(List<String> urls) {
        if (urls == null) return null;
        try {
            return objectMapper.writeValueAsString(urls);
        } catch (Exception e) {
            log.error("[TICKET] 序列化附件失败: {}", e.getMessage());
            return null;
        }
    }

    private List<String> parseAttachments(String json) {
        if (json == null || json.isBlank()) return null;
        try {
            return objectMapper.readValue(json, objectMapper.getTypeFactory().constructCollectionType(List.class, String.class));
        } catch (Exception e) {
            return List.of();
        }
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
