package com.itticket.rag.support;

import java.util.Locale;

/**
 * ============================================================================
 * 角色值域归一化 (Roles)
 * ============================================================================
 *
 * <p>契约 DM-002 枚举目录（specs/01-data-model-strong-types.md:41）与 PRD §5.1
 * （IT服务工单系统PRD-Ultimate.md:89）的 RoleCode 值域为
 * EMPLOYEE / ENGINEER / PLATFORM_ADMIN / KNOWLEDGE_ADMIN；
 * 网关 JWT 与种子数据实际下发 KB_ADMIN，历史数据还存在 supervisor / knowledge_admin 小写值。
 * 本工具把这些变体统一为契约值域，避免状态机守卫（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90）
 * 因大小写或别名而误判。</p>
 *
 * @author IT工单系统研发组 - RAG专项
 */
public final class Roles {

    /** 契约角色码（DM-002 RoleCode） */
    public static final String EMPLOYEE = "EMPLOYEE";
    public static final String ENGINEER = "ENGINEER";
    public static final String PLATFORM_ADMIN = "PLATFORM_ADMIN";
    public static final String KNOWLEDGE_ADMIN = "KNOWLEDGE_ADMIN";

    private Roles() {
    }

    /** 归一为契约角色码；无法识别时返回原值大写形式 */
    public static String normalize(String raw) {
        if (raw == null || raw.isBlank()) {
            return "";
        }
        String role = raw.trim().toUpperCase(Locale.ROOT);
        return switch (role) {
            // 历史/别名值域 → 契约值域
            case "SUPERVISOR" -> PLATFORM_ADMIN;
            case "KB_ADMIN" -> KNOWLEDGE_ADMIN;
            default -> role;
        };
    }

    public static boolean isKnowledgeAdmin(String role) {
        return KNOWLEDGE_ADMIN.equals(normalize(role));
    }

    public static boolean isPlatformAdmin(String role) {
        return PLATFORM_ADMIN.equals(normalize(role));
    }

    public static boolean isEngineer(String role) {
        return ENGINEER.equals(normalize(role));
    }

    /** 可处理知识的角色：知识库管理员或平台管理员 */
    public static boolean canManageKnowledge(String role) {
        return isKnowledgeAdmin(role) || isPlatformAdmin(role);
    }

    /** 可提交审核的角色：知识库管理员、平台管理员或工程师（SM-KNOWLEDGE-001 · specs/03-business-state-machine.md:90「提交审核」行） */
    public static boolean canSubmitReview(String role) {
        return canManageKnowledge(role) || isEngineer(role);
    }
}
