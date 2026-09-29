package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.ticket.entity.Assignment;
import com.itticket.ticket.entity.CategoryRoute;
import com.itticket.ticket.entity.TeamMember;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.AssignmentMapper;
import com.itticket.ticket.mapper.CategoryRouteMapper;
import com.itticket.ticket.mapper.TeamMemberMapper;
import com.itticket.ticket.mapper.TicketMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 自动路由服务 —— PRD-Ultimate F-06 / §12。
 * 分配算法（§12.1）：
 *   1. 分类路由：category_route 按 route_order 取候选团队
 *   2. 团队成员：team_member 取该团队 ACTIVE 工程师
 *   3. 在线可用：过滤 engineer（user 表 active 状态，经 Feign）
 *   4. 加权负载：取当前 OPEN 工单数最少者
 * 路由失败（无候选工程师）→ 工单转 ROUTE_FAILED 自环 + 异常队列（§4）。
 * 响应超时：assignment.response_deadline（10 工作分钟）未响应 → 转派次优工程师（§12.2）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RoutingService {

    private final CategoryRouteMapper categoryRouteMapper;
    private final TeamMemberMapper teamMemberMapper;
    private final AssignmentMapper assignmentMapper;
    private final TicketMapper ticketMapper;
    private final UserClient userClient;
    private final WorkCalendarService workCalendarService;
    private final ExceptionQueueService exceptionQueueService;
    private final NotificationService notificationService;
    private final TicketFlowLogMapper flowLogMapper;

    /** 响应 SLA：10 工作分钟（§12.2） */
    private static final long RESPONSE_DEADLINE_SECONDS = 10 * 60L;

    /**
     * 自动路由：为工单选择工程师。返回分配的工程师 ID；无候选返回 null。
     */
    @Transactional
    public String route(Ticket ticket) {
        String engineerId = selectEngineer(ticket.getCategoryId(), Collections.emptySet());
        if (engineerId == null) {
            log.warn("[路由] 路由失败（无候选工程师）: {} 分类={}", ticket.getTicketId(), ticket.getCategoryId());
            exceptionQueueService.raise("TICKET", ticket.getTicketId(),
                    ExceptionQueueService.TYPE_ROUTE_FAILED,
                    "自动路由失败", "分类【" + ticket.getCategoryId() + "】无可分配工程师", ticket.getPriority());
            // PRD §9.3：路由失败保持 NEW，通知平台管理员
            notifyAdminsRouteFailed(ticket);
            return null;
        }
        assign(ticket, engineerId, null);
        log.info("[路由] 已分配: {} -> {}", ticket.getTicketId(), engineerId);
        return engineerId;
    }

    /** 路由失败时通知所有平台管理员（PRD §9.3）。失败不阻断主流程。 */
    private void notifyAdminsRouteFailed(Ticket ticket) {
        try {
            Result<List<UserInfo>> res = userClient.admins();
            List<UserInfo> admins = (res != null && res.getData() != null) ? res.getData() : List.of();
            for (UserInfo admin : admins) {
                notificationService.sendNotification(ticket.getTicketId(), "ROUTE_FAILED", admin.getUserId());
            }
            if (admins.isEmpty()) {
                log.warn("[路由] 路由失败但无可用平台管理员可通知: {}", ticket.getTicketId());
            }
        } catch (Exception e) {
            log.error("[路由] 通知平台管理员失败（不阻断）: {}", e.getMessage());
        }
    }

    /**
     * 选择工程师：分类路由 → 团队 → 在线工程师 → 负载最少。
     *
     * @param category 工单分类
     * @param exclude  需排除的工程师（转派时排除原处理人）
     */
    public String selectEngineer(String category, Set<String> exclude) {
        // 1. 分类路由：取候选团队（按 route_order）
        List<CategoryRoute> routes = categoryRouteMapper.selectList(
                new QueryWrapper<CategoryRoute>()
                        .eq("category_id", category)
                        .le("effective_at", LocalDateTime.now(java.time.ZoneOffset.UTC))
                        .and(w -> w.isNull("expired_at").or().gt("expired_at", LocalDateTime.now(java.time.ZoneOffset.UTC)))
                        .orderByAsc("route_order"));
        if (routes.isEmpty()) {
            // PRD §9.3：分类无可用候选人 → 保持 NEW 进异常队列，不做兑底分配
            log.warn("[路由] 分类无路由配置: {}", category);
            return null;
        }

        // 2. 团队成员：按团队顺序收集工程师
        Set<String> candidateIds = new LinkedHashSet<>();
        for (CategoryRoute r : routes) {
            List<TeamMember> members = teamMemberMapper.selectList(
                    new QueryWrapper<TeamMember>()
                            .eq("team_id", r.getTeamId())
                            .eq("enabled", true).isNull("left_at"));
            members.forEach(m -> candidateIds.add(m.getEngineerId()));
        }
        candidateIds.removeAll(exclude);
        if (candidateIds.isEmpty()) {
            log.warn("[路由] 候选团队无工程师: {}", category);
            return null;
        }

        // 3. 在线可用：过滤 active 工程师（Feign 查 user）
        Set<String> activeIds = new HashSet<>();
        try {
            Result<List<UserInfo>> res = userClient.engineers();
            if (res != null && res.getData() != null) {
                for (UserInfo u : res.getData()) {
                    activeIds.add(u.getUserId());
                }
            }
        } catch (Exception e) {
            log.error("[路由] 查询工程师列表失败，降级为不过滤在线状态", e);
            activeIds.addAll(candidateIds); // 降级：user-service 不可用时不过滤
        }
        List<String> available = candidateIds.stream()
                .filter(activeIds::contains)
                .collect(Collectors.toList());
        if (available.isEmpty()) {
            log.warn("[路由] 候选工程师均不在线: {}", category);
            return null;
        }

        // 4. 加权负载：OPEN 工单数最少者（简化权重，非终态工单计 1）
        String best = null;
        long bestLoad = Long.MAX_VALUE;
        for (String engId : available) {
            Long load = ticketMapper.selectCount(new QueryWrapper<Ticket>()
                    .eq("assignee_id", engId)
                    .notIn("status", "COMPLETED", "CANCELLED", "CLOSED"));
            long l = load == null ? 0 : load;
            if (l < bestLoad) {
                bestLoad = l;
                best = engId;
            }
        }
        log.info("[路由] 加权负载选择: (负载 {})", best, bestLoad);
        return best;
    }

    /**
     * 分配工单：写 assignment 记录（响应截止 10 工作分钟）+ 更新工单 assignee。
     */
    @Transactional
    public void assign(Ticket ticket, String engineerId, String endReason) {
        LocalDateTime now = LocalDateTime.now(java.time.ZoneOffset.UTC);
        // 结束上一条未关闭的 assignment（转派时）
        if (endReason != null) {
            Assignment last = assignmentMapper.selectOne(new QueryWrapper<Assignment>()
                    .eq("biz_type", "TICKET")
                    .eq("biz_id", ticket.getTicketId())
                    .isNull("end_reason")
                    .orderByDesc("assigned_at")
                    .last("limit 1"));
            if (last != null) {
                Assignment close = new Assignment();
                close.setAssignmentId(last.getAssignmentId());
                close.setEndReason(endReason);
                close.setUpdatedAt(now);
                assignmentMapper.updateById(close);
            }
        }
        // 新建 assignment
        Assignment a = new Assignment();
        a.setAssignmentId("ASG" + UUID.randomUUID().toString().replace("-", "").substring(0, 29));
        a.setBizType("TICKET");
        a.setBizId(ticket.getTicketId());
        a.setEngineerId(engineerId);
        a.setAssignedAt(now);
        a.setResponseDeadline(workCalendarService.addWorkSeconds(now, RESPONSE_DEADLINE_SECONDS));
        a.setCreatedAt(now);
        a.setUpdatedAt(now);
        assignmentMapper.insert(a);

        // 更新工单 assignee
        Ticket upd = new Ticket();
        upd.setTicketId(ticket.getTicketId());
        upd.setAssigneeId(engineerId);
        upd.setUpdatedAt(now);
        ticketMapper.updateById(upd);
    }

    /**
     * 响应超时扫描（每 1 分钟）：assignment 超 response_deadline 未 responded → 转派次优工程师（§12.2）。
     */
    @Scheduled(fixedDelay = 60000, initialDelay = 45000)
    public void scanResponseTimeout() {
        List<Assignment> pending = assignmentMapper.selectList(new QueryWrapper<Assignment>()
                .eq("biz_type", "TICKET")
                .isNull("responded_at")
                .isNull("end_reason")
                .isNotNull("response_deadline")
                .le("response_deadline", LocalDateTime.now(java.time.ZoneOffset.UTC)));
        if (pending.isEmpty()) return;
        for (Assignment a : pending) {
            try {
                transferOnTimeout(a);
            } catch (Exception e) {
                log.error("[路由] 响应超时转派异常: " + a.getAssignmentId(), e);
            }
        }
    }

    /** 响应超时转派：排除当前工程师，选次优；无候选则入异常队列 */
    @Transactional
    public void transferOnTimeout(Assignment current) {
        if (!"TICKET".equals(current.getBizType())) return;
        Ticket ticket = ticketMapper.selectById(current.getBizId());
        if (ticket == null) return;
        String next = selectEngineer(ticket.getCategoryId(), Set.of(current.getEngineerId()));
        if (next == null) {
            log.warn("[路由] 响应超时但无次优工程师: {}", ticket.getTicketId());
            exceptionQueueService.raise("TICKET", ticket.getTicketId(),
                    ExceptionQueueService.TYPE_NO_RESPONSE,
                    "响应超时且无人可转派", "工程师 " + current.getEngineerId() + " 响应超时，无候选工程师", ticket.getPriority());
            return;
        }
        assign(ticket, next, "TIMEOUT");
        TicketFlowLog flow = new TicketFlowLog();
        flow.setTicketId(ticket.getTicketId());
        flow.setFromStatus(ticket.getStatus().getValue());
        flow.setToStatus(ticket.getStatus().getValue());
        flow.setEvent("TICKET_TIMEOUT_TRANSFER");
        flow.setOperatorId("SYSTEM");
        flow.setReason("Response timeout: " + current.getEngineerId() + " -> " + next);
        flow.setOccurredAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
        flowLogMapper.insert(flow);
        log.warn("[路由] 响应超时转派: {} {} -> {}", ticket.getTicketId(), current.getEngineerId(), next);
    }

    /** 标记工程师已响应（首次接单/首次处理时调用，§12.2 响应 SLA） */
    @Transactional
    public void markResponded(String ticketId, String engineerId) {
        Assignment a = assignmentMapper.selectOne(new QueryWrapper<Assignment>()
                .eq("biz_type", "TICKET")
                .eq("biz_id", ticketId)
                .eq("engineer_id", engineerId)
                .isNull("responded_at")
                .isNull("end_reason")
                .orderByDesc("assigned_at")
                .last("limit 1"));
        if (a != null) {
            Assignment upd = new Assignment();
            upd.setAssignmentId(a.getAssignmentId());
            upd.setRespondedAt(LocalDateTime.now(java.time.ZoneOffset.UTC));
            upd.setEndReason("RESPONDED");
            upd.setUpdatedAt(upd.getRespondedAt());
            assignmentMapper.updateById(upd);
        }
    }
}
