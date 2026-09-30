package com.itticket.user.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.user.config.JwtProperties;
import com.itticket.user.dto.*;
import com.itticket.user.entity.User;
import com.itticket.user.entity.UserRoleEntity;
import com.itticket.user.mapper.UserMapper;
import com.itticket.user.mapper.UserRoleMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.any;

/**
 * user-service 对外 JSON 契约的端到端回归（对齐 PRD/spec 中的规范字段命名）：
 *  - 登录响应 / 当前用户 / 内部查询 / 登录选项 / 用户列表 / 账号列表 六个出口
 *    必须输出完全一致的规范身份字段集（snake_case）；
 *  - 列表查询必须显式指定列且按 status=ACTIVE 过滤；
 *  - 非规范字段（display_name、enabled 等历史命名）绝不允许再次出现；
 *  - 请求侧必须接受 snake_case 入参（user_id / role_code / new_password ...）。
 */
class PrdUserContractTest {
    private final ObjectMapper json = new ObjectMapper();

    /**
     * 六个身份输出出口的一致性大体检：
     * 1) 六个出口返回的 JSON 身份字段必须与规范字段集逐项相等（assertIdentity）；
     * 2) 所有用户列表查询使用固定列投影（保证不泄露 password_hash 等敏感列），共 3 次 selectList；
     * 3) 登录选项（loginOptions）只返回 ACTIVE 用户（断言查询条件含 status=ACTIVE）；
     * 4) 非 ACTIVE（含 DISABLED/SUSPENDED 及小写 active 脏数据）用户在登录与 currentUser 被拒，
     *    但内部查询仍原样回读真实状态（内部接口忠于存储，不做修饰）。
     */
    @Test
    void loginAndListsExposeCompletePrdIdentityAndQueryActiveStatus() {
        UserMapper users = mock(UserMapper.class);
        UserRoleMapper roles = mock(UserRoleMapper.class);
        BCryptPasswordEncoder passwords = mock(BCryptPasswordEncoder.class);
        User user = new User();
        user.setUserId("U01");
        user.setEmployeeNo("E01");
        user.setName("Alice");
        user.setDepartmentId("IT");
        user.setIdentitySource("LOCAL");
        user.setStatus("ACTIVE");
        user.setPasswordHash("hash");
        UserRoleEntity role = new UserRoleEntity();
        role.setRoleCode("KNOWLEDGE_ADMIN");
        when(users.selectById("U01")).thenReturn(user);
        when(users.selectList(any())).thenReturn(List.of(user));
        when(roles.selectOne(any())).thenReturn(role);
        when(passwords.matches("secret", "hash")).thenReturn(true);
        JwtProperties jwt = new JwtProperties();
        jwt.setSecret("0123456789012345678901234567890123456789012345678901234567890123");
        UserService service = new UserService(users, roles, mock(com.itticket.user.mapper.TeamAutoJoinMapper.class), passwords, jwt);
        LoginRequest request = new LoginRequest();
        request.setUserId("U01");
        request.setPassword("secret");
        // 六个身份输出出口逐一过一遍契约
        assertIdentity(json.valueToTree(service.login(request).getUser()));
        assertIdentity(json.valueToTree(service.currentUser("U01")));
        var internal = new com.itticket.user.controller.InternalUserController(users, roles);
        assertIdentity(json.valueToTree(internal.getUser("U01").getData()));
        assertIdentity(json.valueToTree(service.loginOptions().get(0)));
        assertIdentity(json.valueToTree(service.listUsers(null).get(0)));
        assertIdentity(json.valueToTree(service.listAllAccounts("PLATFORM_ADMIN").get(0)));
        // 3 次列表查询的列投影必须完全一致，禁止 select * 泄露 password_hash
        ArgumentCaptor<QueryWrapper<User>> queries = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(users, times(3)).selectList(queries.capture());
        for (QueryWrapper<User> query : queries.getAllValues()) {
            assertEquals("user_id,employee_no,name,department_id,status,identity_source", query.getSqlSelect());
        }
        // 登录选项必须只查 ACTIVE 用户（第一个 selectList 来自 loginOptions）
        assertTrue(queries.getAllValues().get(0).getSqlSegment().contains("status"));
        assertTrue(queries.getAllValues().get(0).getParamNameValuePairs().containsValue("ACTIVE"));
        // 非 ACTIVE 状态：登录与当前用户接口拒绝；内部接口原样回读
        for (String status : new String[]{"DISABLED", "SUSPENDED", "active"}) {
            user.setStatus(status);
            assertThrows(com.itticket.common.api.BizException.class, () -> service.login(request));
            assertThrows(com.itticket.common.api.BizException.class, () -> service.currentUser("U01"));
            assertEquals(status, internal.getUser("U01").getData().getStatus());
        }
    }

    /** 规范身份字段集：snake_case 七字段齐全，旧命名 display_name / enabled 不得出现 */
    private void assertIdentity(JsonNode value) {
        assertEquals("U01", value.path("user_id").asText());
        assertEquals("E01", value.path("employee_no").asText());
        assertEquals("Alice", value.path("name").asText());
        assertEquals("IT", value.path("department_id").asText());
        assertEquals("ACTIVE", value.path("status").asText());
        assertEquals("LOCAL", value.path("identity_source").asText());
        assertEquals("KNOWLEDGE_ADMIN", value.path("role").asText());
        assertFalse(value.has("display_name"));
        assertFalse(value.has("enabled"));
    }

    /** 状态必须原样保留（如 SUSPENDED），禁止在实体层塌缩成布尔或改写为 DISABLED */
    @Test
    void preservesNonActiveStatusInsteadOfCollapsingToBoolean() {
        User user = new User();
        user.setStatus("SUSPENDED");
        assertEquals("SUSPENDED", user.getStatus());
    }

    /**
     * 入参契约：所有请求 DTO 必须接受规范 snake_case 键名
     * （前端与外部系统都按规范命名发请求，反序列化失败会导致 400，因此用反序列化回归）。
     */
    @Test
    void accountRequestsAcceptCanonicalSnakeCase() throws Exception {
        CreateUserRequest request = json.readValue("{\"user_id\":\"U01\",\"employee_no\":\"E01\",\"name\":\"Alice\",\"department_id\":\"IT\",\"role_code\":\"ENGINEER\"}", CreateUserRequest.class);
        assertEquals("U01", request.getUserId());
        assertEquals("E01", request.getEmployeeNo());
        assertEquals("IT", request.getDepartmentId());
        assertEquals("ENGINEER", request.getRoleCode());
        assertEquals("U01", json.readValue("{\"user_id\":\"U01\"}", LoginRequest.class).getUserId());
        assertEquals("next", json.readValue("{\"new_password\":\"next\"}", ResetPasswordRequest.class).getNewPassword());
        assertEquals("old", json.readValue("{\"old_password\":\"old\",\"new_password\":\"next\"}", ChangePasswordRequest.class).getOldPassword());
    }
}