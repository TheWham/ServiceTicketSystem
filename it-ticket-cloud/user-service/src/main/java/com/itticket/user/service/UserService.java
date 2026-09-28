package com.itticket.user.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import com.itticket.common.jwt.JwtUtil;
import com.itticket.user.config.JwtProperties;
import com.itticket.user.dto.LoginRequest;
import com.itticket.user.dto.LoginResponse;
import com.itticket.user.entity.User;
import com.itticket.user.enums.UserRole;
import com.itticket.user.enums.UserStatus;
import com.itticket.user.mapper.UserMapper;
import com.itticket.user.vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserMapper userMapper;
    private final BCryptPasswordEncoder passwordEncoder;
    private final JwtProperties jwtProperties;

    /** 登录校验 + 签发 JWT(12h) */
    public LoginResponse login(LoginRequest request) {
        if (request == null || isBlank(request.getUserId()) || isBlank(request.getPassword())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请输入用户ID和密码");
        }
        User user = userMapper.selectById(request.getUserId().trim());
        if (user == null && "kb_admin".equals(request.getUserId().trim())) {
            // 预设知识库管理员演示账号兜底
            if (!"123456".equals(request.getPassword())) {
                throw new BizException(ErrorCode.PARAM_INVALID, "用户名或密码错误");
            }
            String token = JwtUtil.sign(jwtProperties.getSecret(), "kb_admin", "知识库管理员",
                    "knowledge_admin", "IT部", jwtProperties.getTtlHours() * 3600_000L);
            return new LoginResponse(token, new UserVO("kb_admin", "知识库管理员", "knowledge_admin", "IT部"));
        }
        // 不区分「用户不存在」与「密码错误」,避免枚举账号
        if (user == null || isBlank(user.getPasswordHash())
                || !passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "用户名或密码错误");
        }
        if (user.getStatus() != UserStatus.active) {
            throw new BizException(ErrorCode.USER_INVALID, "用户不存在或已禁用");
        }
        String displayName = user.getName();
        String dept = user.getDepartment();
        if (UserRole.knowledge_admin.equals(user.getRole()) || "kb_admin".equals(user.getUserId()) || "孙知识".equals(displayName)) {
            displayName = "知识库管理员";
            dept = "IT部";
        }
        String token = JwtUtil.sign(jwtProperties.getSecret(), user.getUserId(), displayName,
                user.getRole().getValue(), dept, jwtProperties.getTtlHours() * 3600_000L);
        return new LoginResponse(token, new UserVO(user.getUserId(), displayName,
                user.getRole().getValue(), dept));
    }

    /** Mock 登录选项:列出所有活跃用户,role 排序与旧版 CASE 一致(employee→engineer→supervisor→knowledge_admin) */
    public List<UserVO> loginOptions() {
        QueryWrapper<User> qw = new QueryWrapper<>();
        qw.select("user_id", "name", "role", "department")
                .eq("status", UserStatus.active.getValue())
                .last("ORDER BY CASE role WHEN 'employee' THEN 1 WHEN 'engineer' THEN 2 WHEN 'supervisor' THEN 3 WHEN 'knowledge_admin' THEN 4 ELSE 5 END, name");
        List<UserVO> list = new java.util.ArrayList<>(userMapper.selectList(qw).stream()
                .map(u -> {
                    String name = u.getName();
                    String dept = u.getDepartment();
                    if (UserRole.knowledge_admin.equals(u.getRole()) || "kb_admin".equals(u.getUserId()) || "孙知识".equals(name)) {
                        name = "知识库管理员";
                        dept = "IT部";
                    }
                    return new UserVO(u.getUserId(), name, u.getRole().getValue(), dept);
                })
                .toList());
        boolean hasKbAdmin = list.stream().anyMatch(u -> "knowledge_admin".equals(u.getRole()) || "kb_admin".equals(u.getUserId()));
        if (!hasKbAdmin) {
            list.add(new UserVO("kb_admin", "知识库管理员", "knowledge_admin", "IT部"));
        }
        return list;
    }

    /** 用户列表(供派单选择),与旧版 listUsers 一致 */
    public List<UserVO> listUsers(String role) {
        QueryWrapper<User> qw = new QueryWrapper<>();
        qw.select("user_id", "name", "role", "department")
                .eq("status", UserStatus.active.getValue());
        if (role != null && !role.isBlank()) {
            qw.eq("role", UserRole.valueOf(role).getValue());
        }
        qw.orderByAsc("role").orderByAsc("name");
        return userMapper.selectList(qw).stream()
                .map(u -> new UserVO(u.getUserId(), u.getName(), u.getRole().getValue(), u.getDepartment()))
                .toList();
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }
}
