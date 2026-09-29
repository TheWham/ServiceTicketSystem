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

class PrdRoutingStatusTest {
    @Test void unavailableIdentityServiceCannotAssignAnUnverifiedEngineer() {
        CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
        TeamMemberMapper members = mock(TeamMemberMapper.class);
        UserClient users = mock(UserClient.class);
        TicketMapper tickets = mock(TicketMapper.class);
        CategoryRoute route = new CategoryRoute(); route.setTeamId("TEAM01");
        TeamMember member = new TeamMember(); member.setEngineerId("ENG01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of(member));
        when(users.engineers()).thenThrow(new IllegalStateException("Identity service unavailable"));
        RoutingService service = new RoutingService(routes, members, mock(AssignmentMapper.class),
                tickets, users, mock(WorkCalendarService.class), mock(ExceptionQueueService.class),
                mock(NotificationService.class), mock(TicketFlowLogMapper.class));
        assertNull(service.selectEngineer("CATEGORY01", Set.of()));
        verifyNoInteractions(tickets);
    }

    @Test void routingOnlyReadsActiveMembersOfActiveTeams() {
        CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
        TeamMemberMapper members = mock(TeamMemberMapper.class);
        CategoryRoute route = new CategoryRoute(); route.setTeamId("TEAM01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        when(members.selectList(any())).thenReturn(List.of());
        RoutingService service = new RoutingService(routes, members, mock(AssignmentMapper.class),
                mock(TicketMapper.class), mock(UserClient.class), mock(WorkCalendarService.class),
                mock(ExceptionQueueService.class), mock(NotificationService.class), mock(TicketFlowLogMapper.class));
        assertNull(service.selectEngineer("CATEGORY01", Set.of()));
        ArgumentCaptor<QueryWrapper<TeamMember>> query = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(members).selectList(query.capture());
        String sql = query.getValue().getSqlSegment();
        assertTrue(sql.contains("status")); assertFalse(sql.contains("enabled"));
        assertTrue(sql.contains("support_team"));
        assertTrue(query.getValue().getParamNameValuePairs().containsValue("ACTIVE"));
    }
}
