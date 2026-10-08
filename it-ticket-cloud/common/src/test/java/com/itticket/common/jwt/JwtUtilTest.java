package com.itticket.common.jwt;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * JWT 工具类（common.jwt.JwtUtil）的签发/解析契约测试。
 *
 * JwtUtil 是全系统身份信任链的根：user-service 用它签发登录令牌，
 * 网关与各业务服务用同一密钥解析并提取用户身份 claims。
 * 因此这里必须守住三条底线：
 *   1) 签发的 token 能被无损解析回全部业务 claims（自洽性）；
 *   2) 已过期的 token 必须被拒绝（有效期强制）；
 *   3) 用错误密钥签发的 token 必须被拒绝（防伪造）。
 */
class JwtUtilTest {

    /** 与 application.yml 中 dev 环境一致的测试密钥（jjwt 要求 >= 32 字节） */
    private static final String SECRET = "it-ticket-dev-jwt-secret-key-32bytes-minimum!!";

    /**
     * 签发 → 解析 往返测试：
     * 解析出的 subject 及 name/role/dept 三个业务 claims 必须与签发时一致，
     * 且过期时间应落在签发后 (3500, 3600] 秒的窗口内
     * （允许测试本身有最多 100 秒的执行耗时，正常应在毫秒级）。
     */
    @Test
    void signThenParse_roundTrip() {
        String token = JwtUtil.sign(SECRET, "U001", "张小明", "employee", "市场部", 3600_000);
        Claims claims = JwtUtil.parse(SECRET, token);
        assertEquals("U001", claims.getSubject());
        assertEquals("张小明", claims.get(JwtUtil.CLAIM_NAME, String.class));
        assertEquals("employee", claims.get(JwtUtil.CLAIM_ROLE, String.class));
        assertEquals("市场部", claims.get(JwtUtil.CLAIM_DEPT, String.class));
        // 有效期约 1 小时：断言剩余时间 > 3500s 且 <= 3600s
        long diffSeconds = java.time.temporal.ChronoUnit.SECONDS.between(Instant.now(), claims.getExpiration().toInstant());
        org.junit.jupiter.api.Assertions.assertTrue(diffSeconds > 3500 && diffSeconds <= 3600);
    }

    /**
     * 过期令牌必须遭拒：
     * ttlMillis 传负数直接构造一个“已过期”的 token，
     * parse 必须抛 JwtException，保证过期票据无法通过网关认证。
     */
    @Test
    void expiredToken_throws() {
        String token = JwtUtil.sign(SECRET, "U001", "张小明", "employee", null, -1000);
        assertThrows(JwtException.class, () -> JwtUtil.parse(SECRET, token));
    }

    /**
     * 错误密钥必须遭拒：
     * 同一 token 换一把密钥解析必须抛 JwtException，
     * 这是防止攻击者自行伪造签名放行的最后防线。
     */
    @Test
    void wrongSecret_throws() {
        String token = JwtUtil.sign(SECRET, "U001", "张小明", "employee", null, 3600_000);
        assertThrows(JwtException.class, () -> JwtUtil.parse("another-secret-key-32bytes-minimum-length!!", token));
    }
}