package com.itticket.ticket.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.ticket.entity.CategoryRoute;
import com.itticket.ticket.entity.TeamMember;
import com.itticket.ticket.entity.Ticket;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.AssignmentMapper;
import com.itticket.ticket.mapper.CategoryRouteMapper;
import com.itticket.ticket.mapper.TeamMemberMapper;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 自动路由负载均衡：非终态工单数最少（0 单即空闲）的工程师优先；
 * 负载相同时保持候选顺序（团队 route_order 先后）作为平局依据。
 */
class RoutingLoadBalanceTest {

    private RoutingService newService(TeamMemberMapper members, UserClient users, TicketMapper tickets) {
        CategoryRouteMapper routes = mock(CategoryRouteMapper.class);
        CategoryRoute route = new CategoryRoute();
        route.setTeamId("TEAM01");
        when(routes.selectList(any())).thenReturn(List.of(route));
        return new RoutingService(routes, members, mock(AssignmentMapper.class),
                tickets, users, mock(WorkCalendarService.class), mock(ExceptionQueueService.class),
                mock(NotificationService.class), mock(TicketFlowLogMapper.class));
    }

    private List<TeamMember> members(String... engineerIds) {
        List<TeamMember> list = new ArrayList<>();
        for (String id : engineerIds) {
            TeamMember m = new TeamMember();
            m.setEngineerId(id);
            list.add(m);
        }
        return list;
    }

    private UserClient activeUsers(String... ids) {
        UserClient users = mock(UserClient.class);
        List<UserInfo> list = new ArrayList<>();
        for (String id : ids) {
            UserInfo u = new UserInfo();
            u.setUserId(id);
            list.add(u);
        }
        when(users.engineers()).thenReturn(Result.ok(list));
        return users;
    }

    private TicketMapper loads(Map<String, Long> openLoads) {
        TicketMapper tickets = mock(TicketMapper.class);
        List<Map<String, Object>> rows = new ArrayList<>();
        openLoads.forEach((id, cnt) -> {
            Map<String, Object> row = new HashMap<>();
            row.put("assignee_id", id);
            row.put("open_load", cnt);
            rows.add(row);
        });
        when(tickets.selectMaps(any(QueryWrapper.class))).thenReturn(rows);
        return tickets;
    }

    @Test
    void engineerWithFewerOpenTicketsIsPreferred() {
        TeamMemberMapper members = mock(TeamMemberMapper.class);
        when(members.selectList(any())).thenReturn(members("ENG01", "ENG02"));
        // ENG01 持有 5 个未结工单，ENG02 持有 1 个 -> 应派给 ENG02
        RoutingService service = newService(members, activeUsers("ENG01", "ENG02"),
                loads(Map.of("ENG01", 5L, "ENG02", 1L)));
        assertEquals("ENG02", service.selectEngineer("CATEGORY01", Set.of()));
    }

    @Test
    void idleEngineerWinsOverBusyOne() {
        TeamMemberMapper members = mock(TeamMemberMapper.class);
        when(members.selectList(any())).thenReturn(members("ENG01", "ENG02"));
        // ENG02 完全空闲（聚合结果无其行），应优先于有单的 ENG01
        RoutingService service = newService(members, activeUsers("ENG01", "ENG02"),
                loads(Map.of("ENG01", 3L)));
        assertEquals("ENG02", service.selectEngineer("CATEGORY01", Set.of()));
    }

    @Test
    void equalLoadKeepsCandidateOrder() {
        TeamMemberMapper members = mock(TeamMemberMapper.class);
        when(members.selectList(any())).thenReturn(members("ENG01", "ENG02"));
        // 均为 2 单 -> 平局，保持团队在路由配置中的先后（ENG01 在前）
        RoutingService service = newService(members, activeUsers("ENG01", "ENG02"),
                loads(Map.of("ENG01", 2L, "ENG02", 2L)));
        assertEquals("ENG01", service.selectEngineer("CATEGORY01", Set.of()));
    }
}
