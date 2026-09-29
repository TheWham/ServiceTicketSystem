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

class PrdUserContractTest {
    private final ObjectMapper json = new ObjectMapper();

    @Test void loginAndListsExposeCompletePrdIdentityAndQueryActiveStatus() {
        UserMapper users = mock(UserMapper.class);
        UserRoleMapper roles = mock(UserRoleMapper.class);
        BCryptPasswordEncoder passwords = mock(BCryptPasswordEncoder.class);
        User user = new User();
        user.setUserId("U01"); user.setEmployeeNo("E01"); user.setName("Alice");
        user.setDepartmentId("IT"); user.setIdentitySource("LOCAL"); user.setStatus("ACTIVE");
        user.setPasswordHash("hash");
        UserRoleEntity role = new UserRoleEntity(); role.setRoleCode("KNOWLEDGE_ADMIN");
        when(users.selectById("U01")).thenReturn(user);
        when(users.selectList(any())).thenReturn(List.of(user));
        when(roles.selectOne(any())).thenReturn(role);
        when(passwords.matches("secret", "hash")).thenReturn(true);
        JwtProperties jwt = new JwtProperties(); jwt.setSecret("0123456789012345678901234567890123456789012345678901234567890123");
        UserService service = new UserService(users, roles, passwords, jwt);
        LoginRequest request = new LoginRequest(); request.setUserId("U01"); request.setPassword("secret");
        assertIdentity(json.valueToTree(service.login(request).getUser()));
        assertIdentity(json.valueToTree(service.currentUser("U01")));
        var internal = new com.itticket.user.controller.InternalUserController(users, roles);
        assertIdentity(json.valueToTree(internal.getUser("U01").getData()));
        assertIdentity(json.valueToTree(service.loginOptions().get(0)));
        assertIdentity(json.valueToTree(service.listUsers(null).get(0)));
        assertIdentity(json.valueToTree(service.listAllAccounts("PLATFORM_ADMIN").get(0)));
        ArgumentCaptor<QueryWrapper<User>> queries = ArgumentCaptor.forClass(QueryWrapper.class);
        verify(users, times(3)).selectList(queries.capture());
        for (QueryWrapper<User> query : queries.getAllValues()) {
            assertEquals("user_id,employee_no,name,department_id,status,identity_source", query.getSqlSelect());
        }
        assertTrue(queries.getAllValues().get(0).getSqlSegment().contains("status"));
        assertTrue(queries.getAllValues().get(0).getParamNameValuePairs().containsValue("ACTIVE"));
        for (String status : new String[]{"DISABLED", "SUSPENDED", "active"}) {
            user.setStatus(status);
            assertThrows(com.itticket.common.api.BizException.class, () -> service.login(request));
            assertThrows(com.itticket.common.api.BizException.class, () -> service.currentUser("U01"));
            assertEquals(status, internal.getUser("U01").getData().getStatus());
        }
    }

    private void assertIdentity(JsonNode value) {
        assertEquals("U01", value.path("user_id").asText());
        assertEquals("E01", value.path("employee_no").asText());
        assertEquals("Alice", value.path("name").asText());
        assertEquals("IT", value.path("department_id").asText());
        assertEquals("ACTIVE", value.path("status").asText());
        assertEquals("LOCAL", value.path("identity_source").asText());
        assertEquals("KNOWLEDGE_ADMIN", value.path("role").asText());
        assertFalse(value.has("display_name")); assertFalse(value.has("enabled"));
    }

    @Test void preservesNonActiveStatusInsteadOfCollapsingToBoolean() {
        User user = new User(); user.setStatus("SUSPENDED");
        assertEquals("SUSPENDED", user.getStatus());
    }

    @Test void accountRequestsAcceptCanonicalSnakeCase() throws Exception {
        CreateUserRequest request = json.readValue("{\"user_id\":\"U01\",\"employee_no\":\"E01\",\"name\":\"Alice\",\"department_id\":\"IT\",\"role_code\":\"ENGINEER\"}", CreateUserRequest.class);
        assertEquals("U01", request.getUserId()); assertEquals("E01", request.getEmployeeNo());
        assertEquals("IT", request.getDepartmentId()); assertEquals("ENGINEER", request.getRoleCode());
        assertEquals("U01", json.readValue("{\"user_id\":\"U01\"}", LoginRequest.class).getUserId());
        assertEquals("next", json.readValue("{\"new_password\":\"next\"}", ResetPasswordRequest.class).getNewPassword());
        assertEquals("old", json.readValue("{\"old_password\":\"old\",\"new_password\":\"next\"}", ChangePasswordRequest.class).getOldPassword());
    }
}
