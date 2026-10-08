package com.itticket.rag.support;

import java.util.Locale;
import java.util.regex.Pattern;

/** ai-agent-guard 的 PII/注入规则；中文相邻文本也必须脱敏。 */
public final class AiKnowledgeSanitizer {
    private static final Pattern EMAIL = Pattern.compile("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");
    private static final Pattern PHONE = Pattern.compile("(?<![0-9])1[3-9][0-9]{9}(?![0-9])");
    private static final Pattern EMPLOYEE = Pattern.compile("(?<![a-zA-Z0-9_])(?:E[0-9]{4}|U_[a-zA-Z0-9_]+)(?![a-zA-Z0-9_])");
    private static final Pattern ASSET = Pattern.compile("(?<![a-zA-Z0-9])IT-[A-Z]{2,4}-[0-9]{8}(?![a-zA-Z0-9])");
    private static final String[] INJECTION = {"忽略之前指令", "忽略以上指令", "无视之前的", "disregard previous",
            "ignore previous instructions", "你现在是", "you are now", "系统提示词", "system prompt",
            "开发者模式", "developer mode", "dan 模式", "jailbreak"};

    private AiKnowledgeSanitizer() { }

    public static boolean containsInjection(String text) {
        String lower = text.toLowerCase(Locale.ROOT);
        for (String marker : INJECTION) if (lower.contains(marker)) return true;
        return false;
    }

    public static String redact(String text) {
        String value = EMAIL.matcher(text).replaceAll("[邮箱]");
        value = PHONE.matcher(value).replaceAll("[手机号]");
        value = EMPLOYEE.matcher(value).replaceAll("[工号]");
        return ASSET.matcher(value).replaceAll("[资产编号]").trim();
    }
}
