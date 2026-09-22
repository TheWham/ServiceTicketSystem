package com.itticket.common.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 从 gateway 透传的 X-User-* 请求头组装当前用户。
 * 白名单路径由 WebConfig 的 excludePathPatterns 控制。
 */
public class UserContextInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        String userId = request.getHeader("X-User-Id");
        if (userId == null || userId.isBlank()) {
            throw new com.itticket.common.api.BizException(com.itticket.common.api.ErrorCode.NO_AUTH);
        }
        UserContext.set(new UserContext.CurrentUser(
                userId,
                decode(request.getHeader("X-User-Name")),
                request.getHeader("X-User-Role"),
                decode(request.getHeader("X-User-Dept"))));
        return true;
    }

    /** 网关注入的中文值经 URL 编码,此处解码;兼容未编码直连场景 */
    private static String decode(String value) {
        if (value == null) return null;
        try {
            return java.net.URLDecoder.decode(value, java.nio.charset.StandardCharsets.UTF_8);
        } catch (Exception e) {
            return value;
        }
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        UserContext.clear();
    }
}
