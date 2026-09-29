package com.itticket.consultation.support;

import java.security.SecureRandom;
import java.time.format.DateTimeFormatter;

/**
 * 业务 ID 生成(DM-001:不可变 String 业务 ID,由应用服务统一实现)。
 *
 * <p>格式为 {@code 前缀 + yyyyMMdd + 12 位 Crockford Base32 随机段},
 * SessionId 共 22 字符,满足 DM-003 的 CS 前缀与 32 字符上限。
 * 唯一性最终由 MySQL 主键/唯一索引兜底:重复时调用方重试取新 ID(RD-014 同一策略)。
 */
public final class Ids {

    /** 去掉 I、L、O、U,避免人工转录歧义。 */
    private static final char[] ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ".toCharArray();
    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final SecureRandom RANDOM = new SecureRandom();

    public static final String SESSION_PREFIX = "CS";

    private Ids() {
    }

    public static String sessionId() {
        return generate(SESSION_PREFIX, 12);
    }

    public static String messageId() {
        return generate("MSG", 16);
    }

    public static String interactionId() {
        return generate("AIX", 16);
    }

    public static String assignmentId() {
        return generate("ASG", 16);
    }

    public static String slaId() {
        return generate("SLA", 16);
    }

    public static String eventId() {
        return generate("EV", 18);
    }

    public static String auditId() {
        return generate("AUD", 16);
    }

    public static String idempotencyId() {
        return generate("IDK", 16);
    }

    public static String exceptionId() {
        return generate("EXQ", 16);
    }

    private static String generate(String prefix, int randomLength) {
        StringBuilder sb = new StringBuilder(prefix.length() + 8 + randomLength);
        sb.append(prefix).append(DAY.format(Times.nowUtc()));
        for (int i = 0; i < randomLength; i++) {
            sb.append(ALPHABET[RANDOM.nextInt(ALPHABET.length)]);
        }
        return sb.toString();
    }
}
