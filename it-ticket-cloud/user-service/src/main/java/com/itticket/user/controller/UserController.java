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

    /** 对应旧版 getMe:返回 req.currentUser 的四个字段 */
    @GetMapping("/me")
    public Result<UserVO> me() {
        UserContext.CurrentUser user = UserContext.get();
        return Result.ok(new UserVO(user.getUserId(), user.getName(), user.getRole(), user.getDepartment()));
    }

    @GetMapping
    public Result<List<UserVO>> list(@RequestParam(required = false) String role) {
        return Result.ok(userService.listUsers(role));
    }
}
