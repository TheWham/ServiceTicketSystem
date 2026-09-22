package com.itticket.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.api.Result;
import com.itticket.common.jwt.JwtUtil;
import com.itticket.common.user.UserInfo;
import com.itticket.gateway.config.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;

/**
 * JWT 统一鉴权过滤器,替代旧版 mockAuth:
 * 1. 白名单放行(/api/health、login-options、login);
 * 2. 校验 Authorization: Bearer <token>,无效/过期 → 401/40100;
 * 3. 调 user-service 校验用户存在且 active,否则 401/40101(对应旧版 mockAuth 查库校验);
 * 4. 删除客户端伪造的 X-User-* 头,注入网关解析出的 X-User-Id/Name/Role/Dept 后转发。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AuthGlobalFilter implements GlobalFilter, Ordered {

    private static final String BEARER_PREFIX = "Bearer ";
    private static final String USER_HEADER_PREFIX = "x-user-";

    private final JwtProperties jwtProperties;
    private final ObjectMapper objectMapper;
    private final org.springframework.web.reactive.function.client.WebClient.Builder webClientBuilder;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().value();
        String method = request.getMethod().name();

        if (isWhitelisted(path, method)) {
            return chain.filter(exchange);
        }

        String auth = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (!StringUtils.hasText(auth) || !auth.startsWith(BEARER_PREFIX)) {
            return writeError(exchange, 40100, "未登录或登录凭证缺失，请先登录");
        }

        Claims claims;
        try {
            claims = JwtUtil.parse(jwtProperties.getSecret(), auth.substring(BEARER_PREFIX.length()));
        } catch (JwtException e) {
            return writeError(exchange, 40100, "登录已过期或凭证无效，请重新登录");
        }

        String userId = claims.getSubject();
        String name = claims.get(JwtUtil.CLAIM_NAME, String.class);
        String role = claims.get(JwtUtil.CLAIM_ROLE, String.class);
        String dept = claims.get(JwtUtil.CLAIM_DEPT, String.class);

        // 对应旧版 mockAuth 查库校验「用户存在且 active」(40101)
        return resolveUser(userId)
                .flatMap(userInfo -> {
                    if (userInfo == null) {
                        return writeError(exchange, 40101, "用户不存在或已禁用");
                    }
                    if (!"active".equals(userInfo.getStatus())) {
                        return writeError(exchange, 40101, "用户不存在或已禁用");
                    }
                    // 剥离客户端可能伪造的 X-User-* 头,再注入网关解析出的身份
                    ServerHttpRequest mutated = mutateWithUserHeaders(request, userId, name, role, dept);
                    return chain.filter(exchange.mutate().request(mutated).build());
                })
                .onErrorResume(e -> {
                    log.error("[AUTH] 校验用户状态失败: {}", e.getMessage());
                    return writeError(exchange, 50000, "认证服务暂不可用，请稍后重试");
                });
    }

    /** 调 user-service 校验用户;服务不可用时抛错,由上层 onErrorResume 兜底 50000 */
    private Mono<UserInfo> resolveUser(String userId) {
        return webClientBuilder.build()
                .get()
                .uri("http://user-service/api/internal/users/{userId}", userId)
                .retrieve()
                .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Result<UserInfo>>() {
                })
                .timeout(Duration.ofSeconds(3))
                .map(Result::getData);
    }

    private ServerHttpRequest mutateWithUserHeaders(ServerHttpRequest request, String userId, String name, String role, String dept) {
        return request.mutate().headers(headers -> {
            // set() 会替换同名头的全部旧值,即可剥离客户端伪造的 X-User-* 头
            headers.set("X-User-Id", userId);
            // HTTP 头仅支持 ASCII,中文值需 URL 编码(下游 UserContextInterceptor 解码)
            headers.set("X-User-Name", encode(name));
            headers.set("X-User-Role", role == null ? "" : role);
            headers.set("X-User-Dept", encode(dept));
        }).build();
    }

    private static String encode(String value) {
        if (value == null || value.isEmpty()) return "";
        try {
            return java.net.URLEncoder.encode(value, java.nio.charset.StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "";
        }
    }

    private boolean isWhitelisted(String path, String method) {
        return "/api/health".equals(path)
                || ("/api/v1/users/login-options".equals(path) && "GET".equals(method))
                || ("/api/v1/users/login".equals(path) && "POST".equals(method));
    }

    private Mono<Void> writeError(ServerWebExchange exchange, int code, String msg) {
        ServerHttpResponse response = exchange.getResponse();
        // HTTP 状态与旧版对齐:40100/40101 → 401,50000 → 500
        int httpStatus = code == 50000 ? 500 : 401;
        response.setStatusCode(HttpStatus.valueOf(httpStatus));
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] body;
        try {
            body = objectMapper.writeValueAsBytes(Result.err(code, msg));
        } catch (Exception e) {
            body = ("{\"code\":" + code + ",\"msg\":\"" + msg + "\"}").getBytes(StandardCharsets.UTF_8);
        }
        DataBuffer buffer = response.bufferFactory().wrap(body);
        return response.writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return -100;
    }
}
