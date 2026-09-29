package com.itticket.user.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.jwt.JwtUtil;
import com.itticket.user.config.JwtProperties;
import com.itticket.user.dto.LoginRequest;
import com.itticket.user.dto.LoginResponse;
import com.itticket.user.entity.User;
import com.itticket.user.entity.UserRoleEntity;
import com.itticket.user.mapper.UserMapper;
import com.itticket.user.mapper.UserRoleMapper;
import com.itticket.user.vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserMapper userMapper;
    private final UserRoleMapper userRoleMapper;
    private final BCryptPasswordEncoder passwordEncoder;
    private final JwtProperties jwtProperties;

    /** 登录校验 + 签发 JWT(12h)。角色取自 user_role（PRD §20，一人可多角色取最新授予） */
    public LoginResponse login(LoginRequest request) {
        if (request == null || isBlank(request.getUserId()) || isBlank(request.getPassword())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请输入用户ID和密码");
        }
        User user = userMapper.selectById(request.getUserId().trim());
        // 不区分「用户不存在」与「密码错误」,避免枚举账号
        if (user == null || isBlank(user.getPasswordHash())
                || !passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "用户名或密码错误");
        }
        if (!"ACTIVE".equals(user.getStatus())) {
            throw new BizException(ErrorCode.USER_INVALID, "用户不存在或已禁用");
        }
        String role = primaryRole(user.getUserId());
        String token = JwtUtil.sign(jwtProperties.getSecret(), user.getUserId(), user.getName(),
                role, user.getDepartmentId(), jwtProperties.getTtlHours() * 3600_000L);
        return new LoginResponse(token, new UserVO(user.getUserId(), user.getName(), role, user.getDepartmentId()));
    }

    /** Mock 登录选项:列出所有活跃用户（角色经 user_role 关联） */
    public List<UserVO> loginOptions() {
        return userMapper.selectList(new QueryWrapper<User>()
                        .select("user_id", "name", "department_id")
                        .eq("status", "ACTIVE"))
                .stream()
                .map(u -> new UserVO(u.getUserId(), u.getName(), primaryRole(u.getUserId()), u.getDepartmentId()))
                // 与旧版 CASE 排序一致:employee→engineer→其余角色,再按姓名
                .sorted(Comparator
                        .comparingInt((UserVO v) -> roleOrder(v.getRole()))
                        .thenComparing(UserVO::getName))
                .toList();
    }

    /** 用户列表(供派单选择),按角色过滤（user_role 未撤销记录;入参小写,库值大写） */
    public List<UserVO> listUsers(String role) {
        QueryWrapper<User> uw = new QueryWrapper<User>()
                .select("user_id", "name", "department_id")
                .eq("status", "ACTIVE");
        if (role != null && !role.isBlank()) {
            List<String> userIds = userRoleMapper.selectList(new QueryWrapper<UserRoleEntity>()
                            .eq("role_code", role.trim().toUpperCase()).isNull("revoked_at"))
                    .stream().map(UserRoleEntity::getUserId).toList();
            if (userIds.isEmpty()) return List.of();
            uw.in("user_id", userIds);
        }
        return userMapper.selectList(uw).stream()
                .map(u -> new UserVO(u.getUserId(), u.getName(), primaryRole(u.getUserId()), u.getDepartmentId()))
                .sorted(Comparator
                        .comparingInt((UserVO v) -> roleOrder(v.getRole()))
                        .thenComparing(UserVO::getName))
                .toList();
    }

    /** 角色展示排序:employee→engineer→supervisor→其余,与旧版 CASE 一致 */
    private static int roleOrder(String role) {
        return switch (role == null ? "" : role) {
            case "employee" -> 1;
            case "engineer" -> 2;
            case "supervisor" -> 3;
            default -> 4;
        };
    }

    /** 主角色：最新授予且未撤销的角色（PRD §5.1，一人可多角色）;出口统一小写,与下游判断口径一致 */
    private String primaryRole(String userId) {
        UserRoleEntity r = userRoleMapper.selectOne(new QueryWrapper<UserRoleEntity>()
                .eq("user_id", userId).isNull("revoked_at")
                .orderByDesc("granted_at").last("LIMIT 1"));
        // PRD §5.1 角色值域为大写：EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KB_ADMIN
        return r != null && r.getRoleCode() != null ? r.getRoleCode() : "EMPLOYEE";
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }
}
