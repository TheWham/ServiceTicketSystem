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

    /** 角色展示排序:EMPLOYEE→ENGINEER→PLATFORM_ADMIN→KB_ADMIN→其余 */
    private static int roleOrder(String role) {
        return switch (role == null ? "" : role) {
            case "EMPLOYEE" -> 1;
            case "ENGINEER" -> 2;
            case "PLATFORM_ADMIN" -> 3;
            case "KB_ADMIN" -> 4;
            default -> 5;
        };
    }

    // ==================== 账号管理（认证模块） ====================

    /** 密码强度：至少 6 位，含字母+数字（内部系统一期口径） */
    private static final java.util.regex.Pattern PWD_RULE =
            java.util.regex.Pattern.compile("^(?=.*[A-Za-z])(?=.*\\d).{6,32}$");

    private static void checkPassword(String pwd) {
        if (isBlank(pwd) || !PWD_RULE.matcher(pwd).matches()) {
            throw new BizException(ErrorCode.PARAM_INVALID, "密码需 6-32 位且同时包含字母和数字");
        }
    }

    /** 主管新建账号（admin_only，员工无自助注册）。落库 user + user_role */
    @org.springframework.transaction.annotation.Transactional(rollbackFor = Exception.class)
    public UserVO createUser(com.itticket.user.dto.CreateUserRequest req, String operatorRole) {
        requireAdmin(operatorRole);
        if (req == null || isBlank(req.getUserId()) || isBlank(req.getName())
                || isBlank(req.getEmployeeNo()) || isBlank(req.getRoleCode())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请填写完整的账号信息");
        }
        checkPassword(req.getPassword());
        String roleCode = req.getRoleCode().trim().toUpperCase();
        if (!java.util.Set.of("EMPLOYEE", "ENGINEER", "PLATFORM_ADMIN", "KB_ADMIN").contains(roleCode)) {
            throw new BizException(ErrorCode.PARAM_INVALID, "非法角色:" + roleCode);
        }
        String userId = req.getUserId().trim();
        if (userMapper.selectById(userId) != null) {
            throw new BizException(ErrorCode.PARAM_INVALID, "用户ID已存在:" + userId);
        }
        User u = new User();
        u.setUserId(userId);
        u.setEmployeeNo(req.getEmployeeNo().trim());
        u.setName(req.getName().trim());
        u.setDepartmentId(isBlank(req.getDepartmentId()) ? null : req.getDepartmentId().trim());
        u.setStatus("ACTIVE");
        u.setIdentitySource("LOCAL");
        u.setPasswordHash(passwordEncoder.encode(req.getPassword()));
        u.setCreatedAt(java.time.LocalDateTime.now());
        u.setUpdatedAt(java.time.LocalDateTime.now());
        userMapper.insert(u);

        UserRoleEntity ur = new UserRoleEntity();
        ur.setUserId(userId);
        ur.setRoleCode(roleCode);
        ur.setGrantedBy("ADMIN");
        ur.setGrantedAt(java.time.LocalDateTime.now());
        userRoleMapper.insert(ur);
        return new UserVO(userId, u.getName(), roleCode, u.getDepartmentId());
    }

    /** 修改密码（登录用户）：旧密码校验 → 新密码 BCrypt 落库 */
    public void changePassword(String userId, com.itticket.user.dto.ChangePasswordRequest req) {
        if (req == null || isBlank(req.getOldPassword()) || isBlank(req.getNewPassword())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请填写旧密码和新密码");
        }
        User u = userMapper.selectById(userId);
        if (u == null || !passwordEncoder.matches(req.getOldPassword(), u.getPasswordHash())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "旧密码错误");
        }
        checkPassword(req.getNewPassword());
        if (req.getOldPassword().equals(req.getNewPassword())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "新密码不能与旧密码相同");
        }
        u.setPasswordHash(passwordEncoder.encode(req.getNewPassword()));
        u.setUpdatedAt(java.time.LocalDateTime.now());
        userMapper.updateById(u);
    }

    /** 忘记密码（免登录）：工号+姓名+员工号三要素验证身份后重置 */
    public void forgotPassword(com.itticket.user.dto.ForgotPasswordRequest req) {
        if (req == null || isBlank(req.getUserId()) || isBlank(req.getName()) || isBlank(req.getEmployeeNo())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "请填写完整的身份验证信息");
        }
        User u = userMapper.selectById(req.getUserId().trim());
        // 不提示哪一项错，避免枚举账号
        if (u == null || !u.getName().equals(req.getName().trim())
                || !u.getEmployeeNo().equals(req.getEmployeeNo().trim())) {
            throw new BizException(ErrorCode.PARAM_INVALID, "身份验证失败，请核对用户ID、姓名和员工号");
        }
        if (!"ACTIVE".equals(u.getStatus())) {
            throw new BizException(ErrorCode.USER_INVALID, "用户不存在或已禁用");
        }
        checkPassword(req.getNewPassword());
        u.setPasswordHash(passwordEncoder.encode(req.getNewPassword()));
        u.setUpdatedAt(java.time.LocalDateTime.now());
        userMapper.updateById(u);
    }

    /** 主管账号列表（可视化）：全部用户含角色/部门/状态 */
    public List<UserVO> listAllAccounts(String operatorRole) {
        requireAdmin(operatorRole);
        return userMapper.selectList(new QueryWrapper<User>()
                        .select("user_id", "employee_no", "name", "department_id", "status"))
                .stream()
                .map(u -> new UserVO(u.getUserId(), u.getName(), primaryRole(u.getUserId()), u.getDepartmentId(),
                        u.getEmployeeNo(), u.getStatus()))
                .sorted(Comparator.comparingInt((UserVO v) -> roleOrder(v.getRole())).thenComparing(UserVO::getUserId))
                .toList();
    }

    /** 主管重置他人密码 */
    public void resetPassword(String targetUserId, com.itticket.user.dto.ResetPasswordRequest req, String operatorRole) {
        requireAdmin(operatorRole);
        User u = userMapper.selectById(targetUserId);
        if (u == null) {
            throw new BizException(ErrorCode.USER_INVALID, "目标用户不存在");
        }
        checkPassword(req == null ? null : req.getNewPassword());
        u.setPasswordHash(passwordEncoder.encode(req.getNewPassword()));
        u.setUpdatedAt(java.time.LocalDateTime.now());
        userMapper.updateById(u);
    }

    /** 仅主管（平台管理员/知识库管理员）可管理账号 */
    private static void requireAdmin(String role) {
        if (!"PLATFORM_ADMIN".equals(role) && !"KB_ADMIN".equals(role)) {
            throw new BizException(ErrorCode.FORBIDDEN, "仅主管可执行账号管理操作");
        }
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
