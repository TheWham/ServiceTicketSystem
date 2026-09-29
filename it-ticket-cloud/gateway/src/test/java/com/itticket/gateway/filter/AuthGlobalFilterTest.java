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

class AuthGlobalFilterTest {
    private final JwtProperties properties = new JwtProperties();

    private MockServerWebExchange exchange() {
        String jwt = JwtUtil.sign(properties.getSecret(), "U1", "Employee", "EMPLOYEE", "D1", 60000);
        return MockServerWebExchange.from(MockServerHttpRequest.get("/api/v1/users/me")
                .header("Authorization", "Bearer " + jwt)
                .header("X-User-Id", "FORGED")
                .header("X-User-Role", "PLATFORM_ADMIN"));
    }

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
