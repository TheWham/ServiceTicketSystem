package com.itticket.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.jwt.JwtUtil;
import com.itticket.gateway.config.JwtProperties;
import org.junit.jupiter.api.Test;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.*;

/**
 * 网关认证的用户服务降级兜底：
 * - user-service 不可用 / 超时 → 500 + 50000，绝不放行到业务服务
 * - 白名单（登录接口）不依赖 user-service，用户服务挂了也能进
 * - 无 Token / 伪造 Token → 401，不依赖远程调用
 */
class AuthDegradationTest {

    private final JwtProperties properties = new JwtProperties();
    private final ObjectMapper objectMapper = new ObjectMapper();

    private MockServerWebExchange authedExchange(String path) {
        String jwt = JwtUtil.sign(properties.getSecret(), "U1", "Employee", "EMPLOYEE", "D1", 60000);
        return MockServerWebExchange.from(MockServerHttpRequest.get(path)
                .header("Authorization", "Bearer " + jwt));
    }

    private AuthGlobalFilter filterWith(WebClient.Builder builder) {
        return new AuthGlobalFilter(properties, objectMapper, builder);
    }

    private WebClient.Builder failingUserService() {
        return WebClient.builder().exchangeFunction(
                request -> Mono.error(new RuntimeException("Unable to find instance for user-service")));
    }

    @Test
    void userServiceDownIsRejectedWith500AndNeverForwarded() {
        MockServerWebExchange exchange = authedExchange("/api/v1/tickets/page");
        AtomicBoolean forwarded = new AtomicBoolean(false);

        filterWith(failingUserService()).filter(exchange, e -> {
            forwarded.set(true);
            return Mono.empty();
        }).block();

        assertFalse(forwarded.get(), "用户服务故障时绝不能把请求放行到业务服务");
        assertEquals(500, exchange.getResponse().getStatusCode().value());
    }

    @Test
    void userServiceTimeoutIsRejectedWith500InsteadOfHanging() {
        // resolveUser 有 3 秒超时，超时后必须走 50000 兜底而不是挂死或放行
        WebClient.Builder slowUserService = WebClient.builder()
                .exchangeFunction(request -> Mono.never());
        MockServerWebExchange exchange = authedExchange("/api/v1/users/me");
        AtomicBoolean forwarded = new AtomicBoolean(false);

        filterWith(slowUserService).filter(exchange, e -> {
            forwarded.set(true);
            return Mono.empty();
        }).block();

        assertFalse(forwarded.get());
        assertEquals(500, exchange.getResponse().getStatusCode().value());
    }

    @Test
    void whitelistPassesEvenWhenUserServiceDown() {
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.post("/api/v1/users/login").header("Content-Type", "application/json"));
        AtomicBoolean forwarded = new AtomicBoolean(false);

        filterWith(failingUserService()).filter(exchange, e -> {
            forwarded.set(true);
            return Mono.empty();
        }).block();

        assertTrue(forwarded.get(), "登录白名单不受用户服务故障影响");
    }

    @Test
    void missingTokenIsRejectedWith401() {
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/tickets/page"));
        AtomicBoolean forwarded = new AtomicBoolean(false);

        filterWith(failingUserService()).filter(exchange, e -> {
            forwarded.set(true);
            return Mono.empty();
        }).block();

        assertFalse(forwarded.get());
        assertEquals(401, exchange.getResponse().getStatusCode().value());
    }

    @Test
    void forgedBearerTokenIsRejectedWith401() {
        MockServerWebExchange exchange = MockServerWebExchange.from(MockServerHttpRequest
                .get("/api/v1/tickets/page")
                .header("Authorization", "Bearer not-a-real-jwt"));
        AtomicBoolean forwarded = new AtomicBoolean(false);

        filterWith(failingUserService()).filter(exchange, e -> {
            forwarded.set(true);
            return Mono.empty();
        }).block();

        assertFalse(forwarded.get());
        assertEquals(401, exchange.getResponse().getStatusCode().value());
    }
}
