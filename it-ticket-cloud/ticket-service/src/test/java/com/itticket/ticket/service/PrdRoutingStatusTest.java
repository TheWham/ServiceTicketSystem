package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.ticket.entity.CategoryRoute;
import com.itticket.ticket.entity.TeamMember;
import com.itticket.ticket.mapper.*;
import com.itticket.ticket.feign.UserClient;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import java.util.List;
import java.util.Set;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.any;

/**
 * 派单路由（RoutingService）的身份校验与团队成员圈选回归：
 *  - 身份服务（user-service）不可用时，绝不能把未经状态核验的工程师派给工单；
 *  - 团队候选圈选 SQL 必须同时过滤 ACTIVE 团队 + ACTIVE 成员（规范 status 字段）。
 */
class PrdRoutingStatusTest {

    /**
     * 身份服务降级（fail-closed）：UserClient 抛异常时 selectEngineer 返回 null
     * （上层据此落入人工调度/异常队列），且不得读取工单负载数据 ——
     * 如果连候选人状态都无法核验，则没有任何资格参与负载均衡。
     */
    @Test
    void unavailableIdentityServiceCannotAssignAnUnverifiedEngineer() {
        CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
        TeamMemberMapper members = mock(TeamMemberMapper.class);
        UserClient users = mock(UserClient.class);
        TicketMapper tickets = mock(TicketMapper.class);
        CategoryRoute route = new CategoryRoute();
        route.setTeamId("TEAM01");
        TeamMember member = new TeamMember();
        member.setEngineerId("ENG01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of(member));
        when(users.engineers()).thenThrow(new IllegalStateException("Identity service unavailable"));
        RoutingService service = new RoutingService(routes, members, mock(AssignmentMapper.class),
                tickets, users, mock(WorkCalendarService.class), mock(ExceptionQueueService.class),
                mock(NotificationService.class), mock(TicketFlowLogMapper.class));
        assertNull(service.selectEngineer("CATEGORY01", Set.of()));
        verifyNoInteractions(tickets);
    }

    /**
     * 候选圈选回归：查询 team_member 的 SQL 必须包含规范过滤条件 ——
     *  inner join support_team 且双方 status='ACTIVE'。
     * 同时反向断言不得再出现历史字段 enabled（防回退到旧数据模型）。
     */
    @Test
    void routingOnlyReadsActiveMembersOfActiveTeams() {
        CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
        TeamMemberMapper members = mock(TeamMemberMapper.class);
        CategoryRoute route = new CategoryRoute();
        route.setTeamId("TEAM01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of());
        RoutingService service = new RoutingService(routes, members, mock(AssignmentMapper.class),
                mock(TicketMapper.class), mock(UserClient.class), mock(WorkCalendarService.class),
                mock(ExceptionQueueService.class), mock(NotificationService.class), mock(TicketFlowLogMapper.class));
        assertNull(service.selectEngineer("CATEGORY01", Set.of()));
        ArgumentCaptor<QueryWrapper<TeamMember>> query = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(members).selectList(query.capture());
        String sql = query.getValue().getSqlSegment();
        assertTrue(sql.contains("status"));
        assertFalse(sql.contains("enabled"));
        assertTrue(sql.contains("support_team"));
        assertTrue(query.getValue().getParamNameValuePairs().containsValue("ACTIVE"));
    }
}