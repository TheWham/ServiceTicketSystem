package com.itticket.common.jwt;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class JwtUtilTest {

    private static final String SECRET = "it-ticket-dev-jwt-secret-key-32bytes-minimum!!";

    @Test
    void signThenParse_roundTrip() {
        String token = JwtUtil.sign(SECRET, "U001", "张小明", "employee", "市场部", 3600_000);
        Claims claims = JwtUtil.parse(SECRET, token);
        assertEquals("U001", claims.getSubject());
        assertEquals("张小明", claims.get(JwtUtil.CLAIM_NAME, String.class));
        assertEquals("employee", claims.get(JwtUtil.CLAIM_ROLE, String.class));
        assertEquals("市场部", claims.get(JwtUtil.CLAIM_DEPT, String.class));
        // 有效期约 1 小时
        long diffSeconds = java.time.temporal.ChronoUnit.SECONDS.between(Instant.now(), claims.getExpiration().toInstant());
        org.junit.jupiter.api.Assertions.assertTrue(diffSeconds > 3500 && diffSeconds <= 3600);
    }

    @Test
    void expiredToken_throws() {
        String token = JwtUtil.sign(SECRET, "U001", "张小明", "employee", null, -1000);
        assertThrows(JwtException.class, () -> JwtUtil.parse(SECRET, token));
    }

    @Test
    void wrongSecret_throws() {
        String token = JwtUtil.sign(SECRET, "U001", "张小明", "employee", null, 3600_000);
        assertThrows(JwtException.class, () -> JwtUtil.parse("another-secret-key-32bytes-minimum-length!!", token));
    }
}
