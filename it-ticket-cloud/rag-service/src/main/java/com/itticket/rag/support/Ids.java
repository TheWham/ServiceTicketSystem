package com.itticket.rag.support;

import java.util.UUID;

/**
 * ============================================================================
 * 业务主键生成器 (Ids)
 * ============================================================================
 *
 * <p>契约 DM-001：主键使用不可变 String 业务 ID。线上库相关列均为 varchar(32)，
 * 因此统一约束「前缀 + 随机段」总长不超过 32。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
public final class Ids {

    /** 业务主键最大长度（knowledge_article / knowledge_version / ai_interaction 等均为 varchar(32)） */
    public static final int MAX_LENGTH = 32;

    private Ids() {
    }

    /**
     * 生成带前缀的业务 ID，总长不超过 {@link #MAX_LENGTH}。
     *
     * @param prefix 业务前缀，如 art / ver / kt / ev / ai
     */
    public static String next(String prefix) {
        String random = UUID.randomUUID().toString().replace("-", "");
        int room = MAX_LENGTH - prefix.length();
        if (room <= 0) {
            throw new IllegalArgumentException("前缀过长，无法生成 32 位以内的业务 ID: " + prefix);
        }
        return prefix + random.substring(0, Math.min(room, random.length()));
    }

    /** 校验并返回可直接落库的会话 ID（契约 DM-003：SessionId 最大 32 字符） */
    public static boolean fits(String value) {
        return value != null && !value.isBlank() && value.length() <= MAX_LENGTH;
    }
}
