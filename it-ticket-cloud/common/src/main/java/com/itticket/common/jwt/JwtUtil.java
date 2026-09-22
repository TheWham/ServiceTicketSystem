package com.itticket.common.jwt;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.security.Keys;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * JWT 工具(HS256)
 * 签发方:user-service 登录接口;校验方:gateway AuthGlobalFilter。
 * secret 必须两侧一致(默认值一致,生产经 Nacos 配置中心/环境变量下发)。
 * 载荷:sub=userId, name, role, dept, iat, exp(默认 12 小时)。
 */
public final class JwtUtil {

    public static final String CLAIM_NAME = "name";
    public static final String CLAIM_ROLE = "role";
    public static final String CLAIM_DEPT = "dept";

    private JwtUtil() {
    }

    public static String sign(String secret, String userId, String name, String role, String department, long ttlMillis) {
        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        long now = System.currentTimeMillis();
        return Jwts.builder()
                .subject(userId)
                .claim(CLAIM_NAME, name)
                .claim(CLAIM_ROLE, role)
                .claim(CLAIM_DEPT, department == null ? "" : department)
                .issuedAt(new Date(now))
                .expiration(new Date(now + ttlMillis))
                .signWith(key)
                .compact();
    }

    /** 解析并校验签名/有效期,失败抛 JwtException */
    public static Claims parse(String secret, String token) throws JwtException {
        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();
    }
}
