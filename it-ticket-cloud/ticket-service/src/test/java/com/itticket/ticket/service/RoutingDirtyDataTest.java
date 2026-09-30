package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.ticket.entity.Assignment;
import com.itticket.ticket.entity.CategoryRoute;
import com.itticket.ticket.entity.TeamMember;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.AssignmentMapper;
import com.itticket.ticket.mapper.CategoryRouteMapper;
import com.itticket.ticket.mapper.TeamMemberMapper;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

/**
 * 自动路由在脏数据 / 依赖故障下的降级行为：
 * - 路由配置须带生效窗口过滤（SQL 层）
 * - 同一工程师在多个团队成员表里只算一个候选
 * - 负载聚合查询返回的脏行（null/非数值/未知 ID）不使选路崩溃
 * - 转派无后继 → 入异常队列，不留半成品改派
 * - 路由失败通知管理员失败不影响工单落库结果
 */
class RoutingDirtyDataTest {

    private CategoryRouteMapper routes;
    private TeamMemberMapper members;
    private AssignmentMapper assignments;
    private TicketMapper tickets;
    private UserClient users;
    private ExceptionQueueService exceptionQueue;
    private NotificationService notifications;
    private RoutingService service;

    @BeforeEach
    void setUp() {
        routes = mock(CategoryRouteMapper.class);
        members = mock(TeamMemberMapper.class);
        assignments = mock(AssignmentMapper.class);
        tickets = mock(TicketMapper.class);
        users = mock(UserClient.class);
        exceptionQueue = mock(ExceptionQueueService.class);
        notifications = mock(NotificationService.class);
        service = new RoutingService(routes, members, assignments, tickets, users,
                mock(WorkCalendarService.class), exceptionQueue, notifications, mock(TicketFlowLogMapper.class));
    }

    private TeamMember member(String engineerId) {
        TeamMember m = new TeamMember();
        m.setEngineerId(engineerId);
        return m;
    }

    private void activeUsers(String... ids) {
        List<UserInfo> list = new ArrayList<>();
        for (String id : ids) {
            list.add(new UserInfo(id, id, "ENGINEER", "IT", "ACTIVE"));
        }
        when(users.engineers()).thenReturn(Result.ok(list));
    }

    private Ticket ticket(String id, String category) {
        Ticket t = new Ticket();
        t.setTicketId(id);
        t.setCategoryId(category);
        t.setPriority("MEDIUM");
        return t;
    }

    /** 路由配置查询必须带 effective_at / expired_at 窗口过滤，脏的过期配置不能被选中 */
    @Test
    void routeConfigQueryEnforcesEffectiveWindow() {
        when(routes.selectList(any())).thenReturn(List.of());

        assertNull(service.selectEngineer("C_NET", Set.of()));

        ArgumentCaptor<QueryWrapper<CategoryRoute>> captor = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(routes).selectList(captor.capture());
        String sql = captor.getValue().getSqlSegment();
        assertTrue(sql.contains("effective_at"), "路由查询必须过滤生效时间");
        assertTrue(sql.contains("expired_at"), "路由查询必须过滤失效时间");
    }

    /** 同一工程师挂多个团队（脏数据常见形态）→ 候选人去重，正常完成选路 */
    @Test
    void duplicateMembershipAcrossTeamsIsDeduplicated() {
        CategoryRoute r1 = new CategoryRoute();
        r1.setTeamId("T_HW");
        CategoryRoute r2 = new CategoryRoute();
        r2.setTeamId("T_NET");
        when(routes.selectList(any())).thenReturn(List.of(r1, r2));
        when(members.selectList(any())).thenReturn(List.of(member("ENG01")));
        activeUsers("ENG01");
        when(tickets.selectMaps(any(QueryWrapper.class))).thenReturn(List.<Map<String, Object>>of());

        assertEquals("ENG01", service.selectEngineer("C_NET", Set.of()));
        verify(members, times(2)).selectList(any());
    }

    /** 负载聚合结果混入脏行：null ID、未知工程师、null 计数、字符串计数 → 全部忽略不崩溃，空闲者优先 */
    @Test
    void dirtyAggregateRowsDoNotBreakLoadBalancing() {
        CategoryRoute r = new CategoryRoute();
        r.setTeamId("T_HW");
        when(routes.selectList(any())).thenReturn(List.of(r));
        when(members.selectList(any())).thenReturn(List.of(member("ENG01"), member("ENG02")));
        activeUsers("ENG01", "ENG02");

        List<Map<String, Object>> rows = new ArrayList<>();
        Map<String, Object> row1 = new HashMap<>();
        row1.put("assignee_id", null);
        row1.put("open_load", 9L);
        Map<String, Object> row2 = new HashMap<>();
        row2.put("assignee_id", "GHOST");
        row2.put("open_load", 2L);
        Map<String, Object> row3 = new HashMap<>();
        row3.put("assignee_id", "ENG01");
        row3.put("open_load", null);
        Map<String, Object> row4 = new HashMap<>();
        row4.put("assignee_id", "ENG01");
        row4.put("open_load", BigDecimal.valueOf(5));
        Map<String, Object> row5 = new HashMap<>();
        row5.put("assignee_id", "ENG02");
        row5.put("open_load", "not-a-number");
        for (Map<String, Object> row : List.of(row1, row2, row3, row4, row5)) {
            rows.add(row);
        }
        when(tickets.selectMaps(any(QueryWrapper.class))).thenReturn(rows);

        // ENG01 有效负载=5，ENG02 无有效负载行 → 视为 0（空闲），必须选中 ENG02
        assertEquals("ENG02", service.selectEngineer("C_HW", Set.of()));
    }

    /** 全部候选被排除（转派排除原处理人且无人可转）→ null，且不再调用用户服务 */
    @Test
    void allCandidatesExcludedReturnsNullWithoutUserLookup() {
        CategoryRoute r = new CategoryRoute();
        r.setTeamId("T_HW");
        when(routes.selectList(any())).thenReturn(List.of(r));
        when(members.selectList(any())).thenReturn(List.of(member("ENG01")));

        assertNull(service.selectEngineer("C_HW", Set.of("ENG01")));
        verifyNoInteractions(users, tickets);
    }

    /** 响应超时转派无后继工程师 → 入异常队列 NO_RESPONSE，且不写 assignment、不改工单 */
    @Test
    void timeoutTransferWithoutSuccessorRaisesExceptionQueue() {
        Ticket t = ticket("TK01", "C_NET");
        when(tickets.selectById("TK01")).thenReturn(t);
        when(routes.selectList(any())).thenReturn(List.of());
        Assignment current = new Assignment();
        current.setAssignmentId("ASG01");
        current.setBizType("TICKET");
        current.setBizId("TK01");
        current.setEngineerId("ENG01");

        service.transferOnTimeout(current);

        verify(exceptionQueue).raise(eq("TICKET"), eq("TK01"),
                eq(ExceptionQueueService.TYPE_NO_RESPONSE), any(), any(), any());
        verifyNoInteractions(assignments);
        verify(tickets, never()).updateById(any(Ticket.class));
    }

    /** 路由失败：入异常队列 ROUTE_FAILED；通知平台管理员失败（用户服务故障）必须被吞掉不影响主流程 */
    @Test
    void routeFailureRaisesQueueAndSwallowsAdminNotifyFailure() {
        Ticket t = ticket("TK02", "C_ACC");
        when(routes.selectList(any())).thenReturn(List.of());
        when(users.admins()).thenThrow(new IllegalStateException("user-service unavailable"));

        assertNull(service.route(t));

        verify(exceptionQueue).raise(eq("TICKET"), eq("TK02"),
                eq(ExceptionQueueService.TYPE_ROUTE_FAILED), any(), any(), eq("MEDIUM"));
        verifyNoInteractions(assignments);
    }

    /** 路由失败时每个平台管理员都应收到通知 */
    @Test
    void routeFailureNotifiesEachAdmin() {
        Ticket t = ticket("TK03", "C_ACC");
        when(routes.selectList(any())).thenReturn(List.of());
        when(users.admins()).thenReturn(Result.ok(
                List.of(new UserInfo("U_ADM01", "管理员A", "PLATFORM_ADMIN", "IT", "ACTIVE"),
                        new UserInfo("U_ADM02", "管理员B", "PLATFORM_ADMIN", "IT", "ACTIVE"))));

        assertNull(service.route(t));

        verify(notifications).sendNotification("TK03", "ROUTE_FAILED", "U_ADM01");
        verify(notifications).sendNotification("TK03", "ROUTE_FAILED", "U_ADM02");
    }

    /** 非工单类的 assignment（咨询会话等）不能被工单超时转派逻辑误处理 */
    @Test
    void transferOnTimeoutIgnoresNonTicketAssignments() {
        Assignment other = new Assignment();
        other.setAssignmentId("ASG02");
        other.setBizType("CONSULTATION");
        other.setBizId("CS01");
        other.setEngineerId("ENG01");

        assertDoesNotThrow(() -> service.transferOnTimeout(other));

        verifyNoInteractions(tickets, assignments, exceptionQueue);
    }
}
