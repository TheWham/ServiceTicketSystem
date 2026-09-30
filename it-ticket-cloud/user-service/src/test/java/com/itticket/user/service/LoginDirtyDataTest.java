package com.itticket.user.service;

import com.itticket.common.api.BizException;
import com.itticket.user.config.JwtProperties;
import com.itticket.user.dto.LoginRequest;
import com.itticket.user.entity.User;
import com.itticket.user.mapper.UserMapper;
import com.itticket.user.mapper.UserRoleMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * 登录的脏数据 / 防枚举兜底：
 * - 用户不存在、无密码哈希（遗留脏数据）、密码错误 → 统一"用户名或密码错误"，不暴露账号是否存在
 * - 禁用账号 → 拒绝登录
 * - 空凭证在查库前短路
 */
class LoginDirtyDataTest {

    private UserMapper users;
    private BCryptPasswordEncoder passwords;
    private UserService service;

    @BeforeEach
    void setUp() {
        users = mock(UserMapper.class);
        passwords = mock(BCryptPasswordEncoder.class);
        JwtProperties jwt = new JwtProperties();
        jwt.setSecret("0123456789012345678901234567890123456789012345678901234567890123");
        service = new UserService(users, mock(UserRoleMapper.class), passwords, jwt);
    }

    private LoginRequest request(String id, String pwd) {
        LoginRequest r = new LoginRequest();
        r.setUserId(id);
        r.setPassword(pwd);
        return r;
    }

    private User activeUser() {
        User u = new User();
        u.setUserId("U01");
        u.setEmployeeNo("E01");
        u.setName("Alice");
        u.setDepartmentId("IT");
        u.setIdentitySource("LOCAL");
        u.setStatus("ACTIVE");
        u.setPasswordHash("hash");
        return u;
    }

    @Test
    void unknownUserAndWrongPasswordAreIndistinguishable() {
        when(users.selectById("GHOST")).thenReturn(null);
        BizException unknown = assertThrows(BizException.class,
                () -> service.login(request("GHOST", "x")));

        User u = activeUser();
        when(users.selectById("U01")).thenReturn(u);
        when(passwords.matches("bad", "hash")).thenReturn(false);
        BizException wrongPwd = assertThrows(BizException.class,
                () -> service.login(request("U01", "bad")));

        assertEquals(unknown.getMessage(), wrongPwd.getMessage(), "两种失败文案必须一致，避免枚举账号");
    }

    @Test
    void legacyRowWithoutPasswordHashCannotLogin() {
        User u = activeUser();
        u.setPasswordHash(null); // 历史脏数据：无密码哈希
        when(users.selectById("U01")).thenReturn(u);

        assertThrows(BizException.class, () -> service.login(request("U01", "secret")));
        verifyNoInteractions(passwords); // 短路：不应对 null 哈希做 match
    }

    @Test
    void disabledAccountIsRejected() {
        User u = activeUser();
        u.setStatus("DISABLED");
        when(users.selectById("U01")).thenReturn(u);
        when(passwords.matches("secret", "hash")).thenReturn(true);

        BizException e = assertThrows(BizException.class, () -> service.login(request("U01", "secret")));
        assertTrue(e.getMessage().contains("禁用"));
    }

    @Test
    void blankCredentialsAreRejectedBeforeQuery() {
        assertThrows(BizException.class, () -> service.login(request("", "x")));
        assertThrows(BizException.class, () -> service.login(request("U01", "  ")));
        assertThrows(BizException.class, () -> service.login(null));
        verifyNoInteractions(users);
    }
}
