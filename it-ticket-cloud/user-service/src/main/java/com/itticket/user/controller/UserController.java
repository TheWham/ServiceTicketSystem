package com.itticket.user.controller;

import com.itticket.common.api.Result;
import com.itticket.common.web.UserContext;
import com.itticket.user.service.UserService;
import com.itticket.user.vo.UserVO;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/** 当前用户 + 用户列表(需登录) */
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    /** 从身份记录读取当前用户的完整 PRD 投影。 */
    @GetMapping("/me")
    public Result<UserVO> me() {
        UserContext.CurrentUser user = UserContext.get();
        return Result.ok(userService.currentUser(user.getUserId()));
    }

    @GetMapping
    public Result<List<UserVO>> list(@RequestParam(required = false) String role) {
        return Result.ok(userService.listUsers(role));
    }
}
