package com.itticket.ai.ws;

import com.itticket.ai.config.JwtProperties;
import com.itticket.common.jwt.JwtUtil;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * WebSocket 握手鉴权:浏览器 WebSocket API 无法自定义请求头,
 * 故 token 经查询参数传递(?token=xxx),此处用与网关相同的 secret 校验 JWT,
 * 校验通过则把用户身份写入 attributes 供 Handler 使用。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class WsAuthInterceptor implements HandshakeInterceptor {

    private final JwtProperties jwtProperties;

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                   WebSocketHandler wsHandler, Map<String, Object> attributes) {
        String query = request.getURI().getRawQuery();
        String token = queryParam(query, "token");
        if (token == null) {
            log.warn("[WS] 握手缺少 token,已拒绝");
            return false;
        }
        try {
            Claims claims = JwtUtil.parse(jwtProperties.getSecret(), token);
            attributes.put("userId", claims.getSubject());
            attributes.put("name", claims.get(JwtUtil.CLAIM_NAME, String.class));
            attributes.put("role", claims.get(JwtUtil.CLAIM_ROLE, String.class));
            // 员工连接时带上会话ID(按会话收发);客服不带(接收队列广播,接入后再带)
            String sessionId = queryParam(query, "sessionId");
            if (sessionId != null) {
                attributes.put("sessionId", Long.parseLong(sessionId));
            }
            return true;
        } catch (Exception e) {
            log.warn("[WS] 握手 token 校验失败: {}", e.getMessage());
            return false;
        }
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                               WebSocketHandler wsHandler, Exception exception) {
        // 无需处理
    }

    /** 解析查询参数(值做 URL 解码) */
    private static String queryParam(String query, String key) {
        if (query == null) {
            return null;
        }
        for (String pair : query.split("&")) {
            int idx = pair.indexOf('=');
            if (idx > 0 && pair.substring(0, idx).equals(key)) {
                return URLDecoder.decode(pair.substring(idx + 1), StandardCharsets.UTF_8);
            }
        }
        return null;
    }
}
