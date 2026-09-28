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

    /**
     * 登录校验 + 签发 JWT(12h)
     * 支持用工号(user_id)或手机号(phone)登录
     */
    public LoginResponse login(LoginRequest request) {
        if (request == null || isBlank(request.getUserId()) || isBlank(request.getPassword())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请输入账号和密码");
        }
        String account = request.getUserId().trim();
        User user = null;
        // 判断输入的是工号还是手机号：纯数字且11位按手机号查，否则按工号查
        if (account.matches("^1[3-9]\\d{9}$")) {
            // 手机号登录
            QueryWrapper<User> qw = new QueryWrapper<>();
            qw.eq("phone", account);
            user = userMapper.selectOne(qw);
        } else {
            // 工号登录
            user = userMapper.selectById(account);
        }
        // 不区分「用户不存在」与「密码错误」,避免枚举账号
        if (user == null || isBlank(user.getPasswordHash())
                || !passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "账号或密码错误");
        }
        if (user.getStatus() != UserStatus.active) {
            throw new BizException(ErrorCode.USER_INVALID, "用户不存在或已禁用");
        }
        String token = JwtUtil.sign(jwtProperties.getSecret(), user.getUserId(), user.getName(),
                user.getRole().getValue(), user.getDepartment(), jwtProperties.getTtlHours() * 3600_000L);
        return new LoginResponse(token, new UserVO(user.getUserId(), user.getName(),
                user.getRole().getValue(), user.getDepartment()));
    }

    /** Mock 登录选项:列出所有活跃用户,role 排序与旧版 CASE 一致(employee→engineer→supervisor) */
    public List<UserVO> loginOptions() {
        QueryWrapper<User> qw = new QueryWrapper<>();
        qw.select("user_id", "name", "role", "department")
                .eq("status", UserStatus.active.getValue())
                .last("ORDER BY CASE role WHEN 'employee' THEN 1 WHEN 'engineer' THEN 2 WHEN 'supervisor' THEN 3 ELSE 4 END, name");
        return userMapper.selectList(qw).stream()
                // 过滤掉 role 为空的异常数据，避免 NPE
                .filter(u -> u.getRole() != null)
                .map(u -> new UserVO(u.getUserId(), u.getName(), u.getRole().getValue(), u.getDepartment()))
                .toList();
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
                .filter(u -> u.getRole() != null)
                .map(u -> new UserVO(u.getUserId(), u.getName(), u.getRole().getValue(), u.getDepartment()))
                .toList();
    }

    private static boolean isBlank(String s) {
        return s == null || s.isBlank();
    }
}
