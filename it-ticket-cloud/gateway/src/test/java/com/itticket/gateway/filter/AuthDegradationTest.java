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
 * - user-service 不可用 / 超时 -> 500 + 50000，绝不放行到业务服务
 * - 白名单（登录接口）不依赖 user-service，用户服务挂了也能进
 * - 无 Token / 伪造 Token -> 401，不依赖远程调用
 *
 * 设计原则：认证链路采用 fail-closed（故障时拒绝）而非 fail-open，
 * 宁可临时不可用也不能让未验证身份的请求进入业务服务。
 */
class AuthDegradationTest {

    private final JwtProperties properties = new JwtProperties();
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 构造携带合法 JWT 的业务请求（用于验证带票请求在依赖故障时的行为） */
    private MockServerWebExchange authedExchange(String path) {
        String jwt = JwtUtil.sign(properties.getSecret(), "U1", "Employee", "EMPLOYEE", "D1", 60000);
        return MockServerWebExchange.from(MockServerHttpRequest.get(path)
                .header("Authorization", "Bearer " + jwt));
    }

    private AuthGlobalFilter filterWith(WebClient.Builder builder) {
        return new AuthGlobalFilter(properties, objectMapper, builder);
    }

    /** user-service 故障桩：模拟 Nacos 找不到实例 / 连接被拒绝等异常场景 */
    private WebClient.Builder failingUserService() {
        return WebClient.builder().exchangeFunction(
                request -> Mono.error(new RuntimeException("Unable to find instance for user-service")));
    }

    /**
     * user-service 抛异常 -> 必须 500 兜底，并断言过滤器从未把请求转发给下游。
     * 若改为 fail-open（放行），未验证身份的请求将携带伪造头进入业务服务，属于安全事故。
     */
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

    /**
     * user-service 响应超时（用 Mono.never() 模拟永不返回）-> 兜底同样必须是 500。
     * resolveUser 内置 3 秒超时，超时后走降级分支，而不是让网关线程挂死或放行。
     * 注意：该用例会真实等待约 3 秒，属于预期耗时。
     */
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

    /**
     * 登录接口（/users/login）在认证白名单中，不调用 user-service 校验身份，
     * 因此即使 user-service 故障也应正常放行 —— 否则用户服务宕机时所有人都无法登录。
     */
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

    /**
     * 无 Authorization 头：本地即可判定，直接 401，
     * 不应也不需要触发对 user-service 的远程调用（桩在出错状态下也不影响结果）。
     */
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

    /**
     * Bearer 值不是合法 JWT：解析失败直接 401，同样不依赖远程调用结果。
     */
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