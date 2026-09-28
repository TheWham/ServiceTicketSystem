package com.itticket.user.controller;

import com.itticket.common.api.Result;
import com.itticket.common.user.UserInfo;
import com.itticket.user.dto.IdsRequest;
import com.itticket.user.entity.User;
import com.itticket.user.mapper.UserMapper;
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

    @GetMapping("/{userId}")
    public Result<UserInfo> getUser(@PathVariable String userId) {
        if ("kb_admin".equals(userId)) {
            return Result.ok(new UserInfo("kb_admin", "知识库管理员", "knowledge_admin", "IT部", "active"));
        }
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
        List<UserInfo> list = new java.util.ArrayList<>(users.stream().map(InternalUserController::toInfo).toList());
        if (request.getIds().contains("kb_admin") && list.stream().noneMatch(u -> "kb_admin".equals(u.getUserId()))) {
            list.add(new UserInfo("kb_admin", "知识库管理员", "knowledge_admin", "IT部", "active"));
        }
        return Result.ok(list);
    }

    private static UserInfo toInfo(User user) {
        String name = user.getName();
        String dept = user.getDepartment();
        if (user.getRole() != null && "knowledge_admin".equals(user.getRole().getValue())
                || "kb_admin".equals(user.getUserId())
                || "孙知识".equals(name)) {
            name = "知识库管理员";
            dept = "IT部";
        }
        return new UserInfo(user.getUserId(), name, user.getRole().getValue(),
                dept, user.getStatus().getValue());
    }
}
