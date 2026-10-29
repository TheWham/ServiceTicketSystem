package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.ticket.entity.Assignment;
import com.itticket.ticket.entity.CategoryRoute;
import com.itticket.ticket.entity.TeamMember;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.entity.TicketFlowLog;
import com.itticket.ticket.enums.TicketStatus;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.AssignmentMapper;
import com.itticket.ticket.mapper.CategoryRouteMapper;
import com.itticket.ticket.mapper.TeamMemberMapper;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * 自动路由**直派**（2026-10-27 起）—— 选人成功即落分派，工单进入 ASSIGNED 等待工程师接单。
 *
 * <p>与 {@link HitlDispatchApprovalTest} 的分工：那边覆盖**保留但已不接线**的派单草案机制
 * （表 / 控制器 / 管理员审批页仍在，见其类注释的接线状态），这里覆盖路由本身的**当前**行为。
 *
 * <p>去掉草案门的直接后果有三条，逐条钉住：
 * <ol>
 *   <li>工单不再停在 NEW —— 直接到 ASSIGNED，工程师端立刻可见可接单；</li>
 *   <li>不再产生任何派单草案（{@code DispatchDraftService} 零交互）；</li>
 *   <li>重复触发不得二次分派 —— 原实现靠草案唯一键做幂等，直派之后那层保护没了，
 *       改由 route() 自身挡（非 NEW 即跳过）。</li>
 * </ol>
 *
 * <p>选人失败路径不受影响：仍入异常队列、通知管理员、工单保持 NEW。
 */
class RoutingDirectAssignTest {

    /** LambdaUpdateWrapper 需要 MyBatis-Plus 实体元数据注册一次（assign 内部的 updateStatus 用） */
    @BeforeAll
    static void initializeMapping() {
        com.baomidou.mybatisplus.core.metadata.TableInfoHelper.initTableInfo(
                new org.apache.ibatis.builder.MapperBuilderAssistant(
                        new com.baomidou.mybatisplus.core.MybatisConfiguration(), ""),
                Ticket.class);
    }

    private TicketMapper ticketMapper;
    private AssignmentMapper assignments;
    private TicketFlowLogMapper flowLogMapper;
    private NotificationService notifications;
    private ExceptionQueueService exceptionQueue;
    private DispatchDraftService draftService;

    @BeforeEach
    void setUp() {
        ticketMapper = mock(TicketMapper.class);
        assignments = mock(AssignmentMapper.class);
        flowLogMapper = mock(TicketFlowLogMapper.class);
        notifications = mock(NotificationService.class);
        exceptionQueue = mock(ExceptionQueueService.class);
        draftService = mock(DispatchDraftService.class);
    }

    /**
     * 装配被测服务：路由配置 → TEAM01，候选与在岗人员为 {@code engineerIds}。
     *
     * <p>{@code engineerIds} 留空 = 没有候选工程师（走路由失败分支）。
     */
    private RoutingService service(Ticket ticket, String... engineerIds) {
        CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
        CategoryRoute route = new CategoryRoute();
        route.setTeamId("TEAM01");
        when(routes.selectList(any())).thenReturn(List.of(route));

        TeamMemberMapper members = mock(TeamMemberMapper.class);
        when(members.selectList(any())).thenReturn(java.util.Arrays.stream(engineerIds)
                .map(id -> {
                    TeamMember m = new TeamMember();
                    m.setEngineerId(id);
                    return m;
                }).toList());

        UserClient users = mock(UserClient.class);
        when(users.engineers()).thenReturn(Result.ok(java.util.Arrays.stream(engineerIds)
                .map(id -> {
                    UserInfo u = new UserInfo();
                    u.setUserId(id);
                    return u;
                }).toList()));
        when(users.admins()).thenReturn(Result.ok(List.of()));

        // 负载聚合无行 = 候选人完全空闲
        when(ticketMapper.selectMaps(any(QueryWrapper.class))).thenReturn(List.of());
        when(ticketMapper.selectOne(any())).thenReturn(ticket);
        // MyBatis-Plus 的 Wrapper 不回填 Java 对象，doAnswer 模拟 DB 生效：
        // 任何 update 都把工单状态置为 ASSIGNED（assignSetsTicketStatusFromNewToAssigned 同款手法）
        when(ticketMapper.update(any(), any())).thenAnswer(inv -> {
            ticket.setStatus(TicketStatus.ASSIGNED);
            return 1;
        });

        return new RoutingService(routes, members, assignments, ticketMapper, users,
                mock(WorkCalendarService.class), exceptionQueue, notifications,
                flowLogMapper, draftService);
    }

    private Ticket ticket(String id, TicketStatus status) {
        Ticket t = new Ticket();
        t.setTicketId(id);
        t.setStatus(status);
        t.setCategoryId("C_NET");
        t.setPriority("MEDIUM");
        return t;
    }

    // ---------------------------------------------------------------- 直派

    @Test
    void routeAssignsDirectlyAndMarksTicketAssigned() {
        Ticket t = ticket("TK01", TicketStatus.NEW);
        RoutingService routing = service(t, "ENG01");

        RouteOutcome outcome = routing.route(t);

        assertEquals(RouteOutcome.Kind.ASSIGNED, outcome.kind(), "选人成功即直派");
        assertEquals("ENG01", outcome.engineerId(), "结局里要带上被分派人");
        assertNull(outcome.draftId(), "直派不产生草案");

        // ① 工单真的到了 ASSIGNED（不是只落了 assignment 记录 —— 那正是历史 P0 的坑）
        assertEquals(TicketStatus.ASSIGNED, t.getStatus(),
                "路由直派后工单必须为 ASSIGNED，工程师端才可见可接单");

        // ② assignment 记录落在被分派人名下
        ArgumentCaptor<Assignment> assignment = ArgumentCaptor.forClass(Assignment.class);
        verify(assignments).insert(assignment.capture());
        assertEquals("ENG01", assignment.getValue().getEngineerId());

        // ③ 流转日志 NEW → ASSIGNED，且能与工单实际状态对上
        ArgumentCaptor<TicketFlowLog> flow = ArgumentCaptor.forClass(TicketFlowLog.class);
        verify(flowLogMapper).insert(flow.capture());
        assertEquals("NEW", flow.getValue().getFromStatus());
        assertEquals("ASSIGNED", flow.getValue().getToStatus());
        assertEquals("TICKET_ASSIGN", flow.getValue().getEvent());
        assertEquals("SYSTEM", flow.getValue().getOperatorId());

        // ④ 通知工程师接单
        verify(notifications).sendNotification("TK01", "ASSIGNED", "ENG01");
    }

    @Test
    void routeDoesNotProduceDispatchDraft() {
        Ticket t = ticket("TK02", TicketStatus.NEW);
        RoutingService routing = service(t, "ENG01");

        assertEquals(RouteOutcome.Kind.ASSIGNED, routing.route(t).kind());

        // 这是本次改动的核心断言：草案门不再接线，一个草案都不该产生
        verifyNoInteractions(draftService);
    }

    // ---------------------------------------------------------------- 幂等

    @Test
    void routeSkipsTicketThatIsNoLongerNew() {
        Ticket t = ticket("TK03", TicketStatus.ASSIGNED);
        RoutingService routing = service(t, "ENG01");

        assertEquals(RouteOutcome.Kind.SKIPPED, routing.route(t).kind(),
                "已分派的工单不得被再次分派（草案唯一键的幂等保护已由本守卫接手）");

        verify(assignments, never()).insert(any(Assignment.class));
        verifyNoInteractions(draftService);
        verifyNoInteractions(notifications);
    }

    // ---------------------------------------------------------------- 失败路径不变

    @Test
    void routeFailureKeepsTicketNewAndRaisesExceptionQueue() {
        Ticket t = ticket("TK04", TicketStatus.NEW);
        RoutingService routing = service(t);   // 无候选工程师

        assertEquals(RouteOutcome.Kind.ROUTE_FAILED, routing.route(t).kind());

        assertEquals(TicketStatus.NEW, t.getStatus(), "路由失败必须保持 NEW 待管理员处理");
        verify(exceptionQueue).raise(eq("TICKET"), eq("TK04"),
                eq(ExceptionQueueService.TYPE_ROUTE_FAILED), any(), any(), eq("MEDIUM"));
        verify(assignments, never()).insert(any(Assignment.class));
        verifyNoInteractions(draftService);
    }
}