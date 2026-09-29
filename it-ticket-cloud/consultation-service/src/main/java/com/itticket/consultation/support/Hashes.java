package com.itticket.consultation.support;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** 幂等请求摘要(RD-002:相同键但请求摘要不同返回 IDEMPOTENCY_CONFLICT)。 */
public final class Hashes {

    private Hashes() {
    }

    /** 返回 64 位小写十六进制,对应 idempotency_record.request_hash CHAR(64)。 */
    public static String sha256Hex(String raw) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(raw.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("JVM 缺少 SHA-256", e);
        }
    }
}
