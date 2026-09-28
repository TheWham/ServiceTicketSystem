package com.itticket.user.controller;

import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.user.dto.IdsRequest;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.user.entity.User;
import com.itticket.user.entity.UserRoleEntity;
import com.itticket.user.mapper.UserMapper;
import com.itticket.user.mapper.UserRoleMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 内部用户接口,供 gateway(登录态用户校验)与 ticket-service(处理人校验/姓名组装)调用。
 * 路径以 /api/internal 开头,网关不配置该路由 → 外部无法经网关触达。
 */
@RestController
@RequestMapping("/api/internal/users")
@RequiredArgsConstructor
public class InternalUserController {

    private final UserMapper userMapper;
    private final UserRoleMapper userRoleMapper;

    @GetMapping("/{userId}")
    public Result<UserInfo> getUser(@PathVariable String userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            return Result.ok(null);
        }
        return Result.ok(toInfo(user));
    }

    @PostMapping("/batch")
    public Result<List<UserInfo>> batch(@RequestBody IdsRequest request) {
        if (request == null || request.getIds() == null || request.getIds().isEmpty()) {
            return Result.ok(List.of());
        }
        List<User> users = userMapper.selectBatchIds(request.getIds());
        return Result.ok(users.stream().map(this::toInfo).toList());
    }

    /** 查询可用工程师列表（F-06 路由用：user_role 中 ENGINEER 且未撤销、用户 ACTIVE） */
    @GetMapping("/engineers")
    public Result<List<UserInfo>> engineers() {
        List<String> ids = userRoleMapper.selectList(new QueryWrapper<UserRoleEntity>()
                        .eq("role_code", "ENGINEER").isNull("revoked_at"))
                .stream().map(UserRoleEntity::getUserId).toList();
        if (ids.isEmpty()) return Result.ok(List.of());
        List<User> users = userMapper.selectList(new QueryWrapper<User>()
                .in("user_id", ids).eq("status", "ACTIVE"));
        return Result.ok(users.stream().map(u -> toInfo(u, "engineer")).toList());
    }

    private UserInfo toInfo(User user) {
        return toInfo(user, primaryRole(user.getUserId()));
    }

    /** role/status 出口统一小写,与 ticket-service、网关的比较口径一致 */
    private UserInfo toInfo(User user, String role) {
        String status = user.getStatus();
        return new UserInfo(user.getUserId(), user.getName(), role,
                user.getDepartmentId(), status == null ? null : status.toLowerCase());
    }

    private String primaryRole(String userId) {
        UserRoleEntity r = userRoleMapper.selectOne(new QueryWrapper<UserRoleEntity>()
                .eq("user_id", userId).isNull("revoked_at")
                .orderByDesc("granted_at").last("LIMIT 1"));
        return r != null && r.getRoleCode() != null ? r.getRoleCode().toLowerCase() : "employee";
    }
}
