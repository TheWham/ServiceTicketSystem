package com.itticket.user.service;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.itticket.common.api.BizException;
import com.itticket.user.entity.*;
import com.itticket.user.mapper.*;
import com.itticket.user.config.JwtProperties;
import com.itticket.user.dto.LoginRequest;
import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

/**
 * 规范数据模型（01-data-model-strong-types.md）在 user-service 侧的落地回归测试：
 *  - 实体与遗留库表/列名的映射不能被改动（`user` 表名、name / creator_id 列）；
 *  - 用户状态沿用字符串枚举语义（ACTIVE / DISABLED），不得塌缩成布尔；
 *  -  KNOWLEDGE_ADMIN（知识库管理员）不得拥有账号管理权限 —— 四角色职责边界；
 *  - 库中残留未知角色编码的用户无法伪装成员工通过认证。
 */
class CanonicalUserTest {

    /**
     * 表/列映射回归：
     * `user` 是 MySQL 保留字，@TableName 必须带反引号；历史库列 name、creator_id 不可改名，
     * 否则 SQL 会直接报错。同时验证 status 字段保持字符串语义且 DISABLED 可读回。
     */
    @Test
    void canonicalUserAndDraftMappingPreserveLegacyDisplay() throws Exception {
        assertEquals("`user`", User.class.getAnnotation(TableName.class).value());
        assertEquals("name", User.class.getDeclaredField("name").getAnnotation(TableField.class).value());
        assertEquals("creator_id", TicketDraft.class.getDeclaredField("userId").getAnnotation(TableField.class).value());
        User user = new User();
        user.setStatus("ACTIVE");
        assertEquals("ACTIVE", user.getStatus());
        user.setStatus("DISABLED");
        assertEquals("DISABLED", user.getStatus());
    }

    /**
     * 四角色权限边界：知识库管理员（含历史别名 KB_ADMIN）只能维护知识库，
     * 调账号全量列表必须抛 BizException，管理员范围仅限 PLATFORM_ADMIN。
     */
    @Test
    void knowledgeAdministratorCannotManageAccounts() {
        UserService service = new UserService(mock(UserMapper.class), mock(UserRoleMapper.class),
                mock(com.itticket.user.mapper.TeamAutoJoinMapper.class), mock(BCryptPasswordEncoder.class), new JwtProperties());
        assertThrows(BizException.class, () -> service.listAllAccounts("KNOWLEDGE_ADMIN"));
        assertThrows(BizException.class, () -> service.listAllAccounts("KB_ADMIN"));
    }

    /**
     * 脏数据兜底：库里若残留 role_code=UNKNOWN 之类的角色，即使密码正确，
     * 登录也必须被拒绝（BizException），绝不能按某种默认角色放行。
     */
    @Test
    void unknownStoredRoleCannotAuthenticateAsEmployee() {
        UserMapper users = mock(UserMapper.class);
        UserRoleMapper roles = mock(UserRoleMapper.class);
        BCryptPasswordEncoder passwords = mock(BCryptPasswordEncoder.class);
        User user = new User();
        user.setUserId("U01");
        user.setStatus("ACTIVE");
        user.setPasswordHash("hash");
        UserRoleEntity role = new UserRoleEntity();
        role.setRoleCode("UNKNOWN");
        when(users.selectById("U01")).thenReturn(user);
        when(roles.selectOne(any())).thenReturn(role);
        when(passwords.matches("secret", "hash")).thenReturn(true);
        LoginRequest request = new LoginRequest();
        request.setUserId("U01");
        request.setPassword("secret");
        UserService service = new UserService(users, roles,
                mock(com.itticket.user.mapper.TeamAutoJoinMapper.class), passwords, new JwtProperties());
        assertThrows(BizException.class, () -> service.login(request));
    }
}