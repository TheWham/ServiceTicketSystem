package com.itticket.common.web;

import com.itticket.common.api.BizException;
import com.itticket.common.api.ErrorCode;
import lombok.Getter;

/**
 * 当前登录用户(由 gateway 校验 JWT 后透传的 X-User-* 头组装)
 * 对应旧版 req.currentUser。
 */
@Getter
public class UserContext {

    private static final ThreadLocal<CurrentUser> HOLDER = new ThreadLocal<>();

    public static void set(CurrentUser user) {
        HOLDER.set(user);
    }

    public static CurrentUser get() {
        CurrentUser user = HOLDER.get();
        if (user == null) {
            // 直连服务端口绕过网关时触发,与旧版 mockAuth 缺头行为一致
            throw new BizException(ErrorCode.NO_AUTH);
        }
        return user;
    }

    public static void clear() {
        HOLDER.remove();
    }

    /** 角色守卫,对应旧版 requireRole;msg 与旧版逐字一致 */
    public static void checkRole(CurrentUser user, String... roles) {
        for (String role : roles) {
            if (role.equals(user.getRole())) {
                return;
            }
        }
        throw new BizException(ErrorCode.FORBIDDEN, "需要 " + String.join(" 或 ", roles) + " 权限");
    }

    @lombok.Value
    public static class CurrentUser {
        String userId;
        String name;
        String role;
        String department;
    }
}
