package com.itticket.user.controller;

import com.itticket.common.api.Result;
import com.itticket.user.dto.LoginRequest;
import com.itticket.user.dto.LoginResponse;
import com.itticket.user.service.UserService;
import com.itticket.user.vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** 登录 + Mock 登录选项(均在网关白名单内,免认证) */
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
}
