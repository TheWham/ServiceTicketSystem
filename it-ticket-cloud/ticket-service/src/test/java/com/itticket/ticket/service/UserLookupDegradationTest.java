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
 * - Feign 抛错 / 返回 null -> 姓名置空，列表仍返回
 * - 脏数据（user_id 为 null 的用户记录）-> 不抛 500，正常记录可回填
 * - 重复 user_id 记录 -> 保留第一条，不抛 Duplicate key
 *
 * 被测的是 TicketService 内部批量查用户姓名的私有方法 batchUsers
 * （通过反射调用，避免为测试扩大可见性）：它负责把列表里的 creator_id/assignee_id
 * 批量翻译成姓名。其降级原则：姓名是展示增强信息，缺失时展示单号即可，
 * 绝不允许姓名回填失败导致整个工单列表 500。
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

    /** user-service 整体不可用：回填结果为空 Map（列表姓名列显示单号兜底），不向上抛异常 */
    @Test
    void feignFailureDegradesToEmptyNames() throws Exception {
        when(userClient.batch(any(IdsRequest.class))).thenThrow(new RuntimeException("user-service down"));
        assertTrue(invoke(List.of("U1")).isEmpty());
    }

    /** 返回包装为 null、或 data 为 null 的两种空响应形态：同样降级为空 Map */
    @Test
    void nullResultDegradesToEmptyNames() throws Exception {
        when(userClient.batch(any(IdsRequest.class))).thenReturn(null);
        assertTrue(invoke(List.of("U1")).isEmpty());
        when(userClient.batch(any(IdsRequest.class))).thenReturn(Result.ok(null));
        assertTrue(invoke(List.of("U1")).isEmpty());
    }

    /** 响应里混入 user_id=null 的脏行：跳过脏行，正常用户的姓名仍能成功回填 */
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

    /** 同一 user_id 出现两条（理论不应发生）：保留先到者，Collectors.toMap 不得抛 IllegalStateException */
    @Test
    void duplicateUserIdKeepsFirstEntry() throws Exception {
        when(userClient.batch(any(IdsRequest.class))).thenReturn(Result.ok(List.of(
                new UserInfo("U1", "张三", "ENGINEER", "IT", "ACTIVE"),
                new UserInfo("U1", "张三-旧", "ENGINEER", "IT", "ACTIVE"))));
        Map<String, UserInfo> result = invoke(List.of("U1"));
        assertEquals(1, result.size());
        assertEquals("张三", result.get("U1").getName());
    }

    /** 空 ID 集合（空列表或 null）直接短路，避免一次无意义的远程调用 */
    @Test
    void emptyIdListSkipsRemoteCall() throws Exception {
        assertTrue(invoke(List.of()).isEmpty());
        assertTrue(invoke(null).isEmpty());
    }
}