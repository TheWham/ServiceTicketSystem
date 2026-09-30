package com.itticket.gateway.filter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itticket.common.jwt.JwtUtil;
import com.itticket.gateway.config.JwtProperties;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.concurrent.atomic.AtomicReference;
import static org.junit.jupiter.api.Assertions.*;

/**
 * 网关全局认证过滤器（AuthGlobalFilter）的核心契约测试。
 *
 * 两条必须守住的底线：
 *   1) 客户端自带的 X-User-Id / X-User-Role 头一律视为伪造，
 *      必须被网关用 user-service 返回的权威身份重写后再转发给业务服务；
 *   2) 只有 user-service 返回 status = ACTIVE 的用户才允许进入业务服务，
 *      DISABLED / 未知状态 / 空值一律 401 拦截。
 *
 * 测试用 MockServerWebExchange + 内存 WebClient 桩，不依赖任何真实远程服务。
 */
class AuthGlobalFilterTest {
    private final JwtProperties properties = new JwtProperties();

    /**
     * 构造一个“同时携带合法 JWT 和伪造身份头”的请求：
     * JWT 声明的角色是 EMPLOYEE，而伪造头却声称自己是 PLATFORM_ADMIN ——
     * 这正是过滤器必须擦除并重写的场景。
     */
    private MockServerWebExchange exchange() {
        String jwt = JwtUtil.sign(properties.getSecret(), "U1", "Employee", "EMPLOYEE", "D1", 60000);
        return MockServerWebExchange.from(MockServerHttpRequest.get("/api/v1/users/me")
                .header("Authorization", "Bearer " + jwt)
                .header("X-User-Id", "FORGED")
                .header("X-User-Role", "PLATFORM_ADMIN"));
    }

    /**
     * 构造一个 user-service 桩：无论请求什么都返回指定 status 的用户数据。
     * 用于在不启动 user-service 的情况下验证过滤器对不同用户状态的处理分支。
     */
    private AuthGlobalFilter filter(String status) {
        String json = """
                {"code":0,"msg":"success","data":{
                  "user_id":"U1","employee_no":"E1","name":"Employee","department_id":"D1",
                  "status":"%s","identity_source":"LOCAL","role":"EMPLOYEE"}}
                """.formatted(status);
        WebClient.Builder builder = WebClient.builder().exchangeFunction(request -> Mono.just(
                ClientResponse.create(HttpStatus.OK).header("Content-Type", MediaType.APPLICATION_JSON_VALUE).body(json).build()));
        return new AuthGlobalFilter(properties, new ObjectMapper(), builder);
    }

    /**
     * 核心防篡改断言：用户 ACTIVE 时放行，
     * 且转发给下游的身份头（X-User-Id=X-User-Role）必须取自 user-service 的权威数据，
     * 绝不能是客户端伪造的 "FORGED" / "PLATFORM_ADMIN"。
     */
    @Test
    void activeStatusPassesAndClientIdentityHeadersAreReplaced() {
        MockServerWebExchange exchange = exchange();
        AtomicReference<String> role = new AtomicReference<>();
        AtomicReference<String> id = new AtomicReference<>();
        filter("ACTIVE").filter(exchange, forwarded -> {
            id.set(forwarded.getRequest().getHeaders().getFirst("X-User-Id"));
            role.set(forwarded.getRequest().getHeaders().getFirst("X-User-Role"));
            return Mono.empty();
        }).block();
        assertEquals("U1", id.get());
        assertEquals("EMPLOYEE", role.get());
    }

    /**
     * 停用/未知/空状态一律 401，且 chain.filter 绝不允许被触发
     * （用 fail() 硬断言“一旦有转发发生测试立即失败”）。
     */
    @Test
    void disabledAndUnknownStatusesCannotReachBusinessServices() {
        for (String status : new String[]{"DISABLED", "UNKNOWN", ""}) {
            MockServerWebExchange exchange = exchange();
            filter(status).filter(exchange, forwarded -> {
                fail("An inactive user must not be forwarded");
                return Mono.empty();
            }).block();
            assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        }
    }
}