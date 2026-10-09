package com.itticket.user.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.user.dto.ChangeRoleRequest;
import com.itticket.user.dto.ChangePasswordRequest;
import com.itticket.user.dto.CreateUserRequest;
import com.itticket.user.dto.ForgotPasswordRequest;
import com.itticket.user.dto.LoginRequest;
import com.itticket.user.dto.LoginResponse;
import com.itticket.user.dto.ResetPasswordRequest;
import com.itticket.user.service.UserService;
import com.itticket.user.vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** 认证与账号管理。login/login-options/forgot-password 在网关白名单免认证，其余需登录 */
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class AuthController {

    private final UserService userService;

    @PostMapping("/login")
    public Result<LoginResponse> login(@RequestBody LoginRequest request) {
        return Result.ok("登录成功", userService.login(request));
    }

    @GetMapping("/login-options")
    public Result<List<UserVO>> loginOptions() {
        return Result.ok(userService.loginOptions());
    }

    /** 忘记密码（免登录）：工号+姓名+员工号三要素验证后重置 */
    @PostMapping("/forgot-password")
    public Result<Void> forgotPassword(@RequestBody ForgotPasswordRequest request) {
        userService.forgotPassword(request);
        return Result.ok("密码已重置，请使用新密码登录", null);
    }

    /** 修改密码（登录用户）：旧密码校验 */
    @PostMapping("/change-password")
    public Result<Void> changePassword(@RequestBody ChangePasswordRequest request) {
        userService.changePassword(currentUserId(), request);
        return Result.ok("密码修改成功", null);
    }

    /** 主管新建账号 */
    @PostMapping("/accounts")
    public Result<UserVO> createAccount(@RequestBody CreateUserRequest request) {
        return Result.ok("账号创建成功", userService.createUser(request, currentRole()));
    }

    /** 主管账号列表（可视化） */
    @GetMapping("/accounts")
    public Result<List<UserVO>> listAccounts() {
        return Result.ok(userService.listAllAccounts(currentRole()));
    }

    /** 主管修改用户角色：撤销原角色授权并授予新角色（下次登录生效） */
    @PutMapping("/accounts/{userId}/role")
    public Result<UserVO> changeRole(@PathVariable("userId") String userId,
                                     @RequestBody ChangeRoleRequest request) {
        return Result.ok("角色修改成功", userService.changeRole(userId, request, currentUserId(), currentRole()));
    }

    /** 主管重置他人密码 */
    @PostMapping("/accounts/{userId}/reset-password")
    public Result<Void> resetPassword(@PathVariable("userId") String userId,
                                      @RequestBody ResetPasswordRequest request) {
        userService.resetPassword(userId, request, currentRole());
        return Result.ok("密码已重置", null);
    }

    private static String currentUserId() {
        UserContext.CurrentUser u = UserContext.get();
        if (u == null || u.getUserId() == null) {
            throw new com.itticket.common.api.BizException(
                    com.itticket.common.api.ErrorCode.USER_INVALID, "未登录或登录已过期");
        }
        return u.getUserId();
    }

    private static String currentRole() {
        UserContext.CurrentUser u = UserContext.get();
        return u == null ? null : u.getRole();
    }
}
