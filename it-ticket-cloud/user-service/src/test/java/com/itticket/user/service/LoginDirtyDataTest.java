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
 * - 用户不存在、无密码哈希（遗留脏数据）、密码错误 -> 统一"用户名或密码错误"，不暴露账号是否存在
 * - 禁用账号 -> 拒绝登录
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
        service = new UserService(users, mock(UserRoleMapper.class),
                mock(com.itticket.user.mapper.TeamAutoJoinMapper.class), passwords, jwt);
    }

    private LoginRequest request(String id, String pwd) {
        LoginRequest r = new LoginRequest();
        r.setUserId(id);
        r.setPassword(pwd);
        return r;
    }

    /** 一条完全正常的 ACTIVE 用户数据，各用例在此基础上制造“脏数据”变体 */
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

    /**
     * 防账号枚举：用户不存在 与 密码错误 两种场景必须返回完全一致的报错文案，
     * 否则攻击者可通过报错差异批量探测哪些账号真实存在。
     */
    @Test
    void unknownUserAndWrongPasswordAreIndistinguishable() {
        // 场景一：账号不存在
        when(users.selectById("GHOST")).thenReturn(null);
        BizException unknown = assertThrows(BizException.class,
                () -> service.login(request("GHOST", "x")));

        // 场景二：账号存在但密码不匹配
        User u = activeUser();
        when(users.selectById("U01")).thenReturn(u);
        when(passwords.matches("bad", "hash")).thenReturn(false);
        BizException wrongPwd = assertThrows(BizException.class,
                () -> service.login(request("U01", "bad")));

        assertEquals(unknown.getMessage(), wrongPwd.getMessage(), "两种失败文案必须一致，避免枚举账号");
    }

    /**
     * 遗留脏数据：库中 password_hash 为 NULL 的老账号。
     * 必须在调用 BCrypt 比较前短路拒绝 —— 否则 BCryptPasswordEncoder 对 null 哈希
     * 会抛出未受控异常，且绝不允许“空密码哈希匹配成功”之类的绕过。
     */
    @Test
    void legacyRowWithoutPasswordHashCannotLogin() {
        User u = activeUser();
        u.setPasswordHash(null); // 历史脏数据：无密码哈希
        when(users.selectById("U01")).thenReturn(u);

        assertThrows(BizException.class, () -> service.login(request("U01", "secret")));
        verifyNoInteractions(passwords); // 短路：不应对 null 哈希做 match
    }

    /**
     * 禁用账号即使密码正确也不得登录，且报错文案需明确包含“禁用”以引导用户联系管理员。
     * （注意：与“密码错误”不同，禁用提示可以暴露原因 —— 账号存在性已通过密码验证确认。）
     */
    @Test
    void disabledAccountIsRejected() {
        User u = activeUser();
        u.setStatus("DISABLED");
        when(users.selectById("U01")).thenReturn(u);
        when(passwords.matches("secret", "hash")).thenReturn(true);

        BizException e = assertThrows(BizException.class, () -> service.login(request("U01", "secret")));
        assertTrue(e.getMessage().contains("禁用"));
    }

    /**
     * 空用户名 / 纯空白密码 / 整个请求体为 null：都应在查库前就短路抛出 BizException，
     * 用 verifyNoInteractions(users) 硬断言没有发生任何数据库访问。
     */
    @Test
    void blankCredentialsAreRejectedBeforeQuery() {
        assertThrows(BizException.class, () -> service.login(request("", "x")));
        assertThrows(BizException.class, () -> service.login(request("U01", "  ")));
        assertThrows(BizException.class, () -> service.login(null));
        verifyNoInteractions(users);
    }
}