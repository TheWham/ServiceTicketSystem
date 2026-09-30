package com.itticket.ticket.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.ticket.feign.IdsRequest;
import com.itticket.ticket.feign.UserClient;
import com.itticket.ticket.mapper.AttachmentMapper;
import com.itticket.ticket.mapper.CategoryMapper;
import com.itticket.ticket.mapper.TicketFlowLogMapper;
import com.itticket.ticket.mapper.TicketMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Collection;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * 工单列表的姓名回填降级（user-service 故障不阻塞列表）：
 * - Feign 抛错 / 返回 null → 姓名置空，列表仍返回
 * - 脏数据（user_id 为 null 的用户记录）→ 不抛 500，正常记录可回填
 * - 重复 user_id 记录 → 保留第一条，不抛 Duplicate key
 */
class UserLookupDegradationTest {

    private UserClient userClient;
    private TicketService service;
    private Method batchUsers;

    @BeforeEach
    void setUp() throws Exception {
        userClient = mock(UserClient.class);
        service = new TicketService(
                mock(TicketMapper.class), mock(CategoryMapper.class), mock(AttachmentMapper.class),
                mock(TicketFlowLogMapper.class), mock(com.itticket.ticket.mapper.TicketPurgeMapper.class), mock(TicketNoGenerator.class),
                mock(NotificationService.class), userClient, mock(SlaService.class),
                mock(RoutingService.class), mock(ExceptionQueueService.class),
                mock(ConsultationConvertNotifier.class), new ObjectMapper());
        batchUsers = TicketService.class.getDeclaredMethod("batchUsers", Collection.class);
        batchUsers.setAccessible(true);
    }

    @SuppressWarnings("unchecked")
    private Map<String, UserInfo> invoke(Collection<String> ids) throws Exception {
        return (Map<String, UserInfo>) batchUsers.invoke(service, ids);
    }

    @Test
    void feignFailureDegradesToEmptyNames() throws Exception {
        when(userClient.batch(any(IdsRequest.class))).thenThrow(new RuntimeException("user-service down"));
        assertTrue(invoke(List.of("U1")).isEmpty());
    }

    @Test
    void nullResultDegradesToEmptyNames() throws Exception {
        when(userClient.batch(any(IdsRequest.class))).thenReturn(null);
        assertTrue(invoke(List.of("U1")).isEmpty());
        when(userClient.batch(any(IdsRequest.class))).thenReturn(Result.ok(null));
        assertTrue(invoke(List.of("U1")).isEmpty());
    }

    @Test
    void dirtyRowWithNullUserIdDoesNotBreakValidEntries() throws Exception {
        UserInfo broken = new UserInfo();
        broken.setUserId(null);
        broken.setName("脏数据用户");
        when(userClient.batch(any(IdsRequest.class))).thenReturn(Result.ok(List.of(
                broken, new UserInfo("U1", "张三", "ENGINEER", "IT", "ACTIVE"))));
        // 脏行（null user_id）不导致 500，正常用户的姓名仍能回填
        Map<String, UserInfo> result = invoke(List.of("U1"));
        assertEquals("张三", result.get("U1").getName());
    }

    @Test
    void duplicateUserIdKeepsFirstEntry() throws Exception {
        when(userClient.batch(any(IdsRequest.class))).thenReturn(Result.ok(List.of(
                new UserInfo("U1", "张三", "ENGINEER", "IT", "ACTIVE"),
                new UserInfo("U1", "张三-旧", "ENGINEER", "IT", "ACTIVE"))));
        Map<String, UserInfo> result = invoke(List.of("U1"));
        assertEquals(1, result.size());
        assertEquals("张三", result.get("U1").getName());
    }

    @Test
    void emptyIdListSkipsRemoteCall() throws Exception {
        assertTrue(invoke(List.of()).isEmpty());
        assertTrue(invoke(null).isEmpty());
    }
}
