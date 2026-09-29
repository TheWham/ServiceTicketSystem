package com.itticket.consultation.statemachine;

import com.itticket.consultation.enums.RoleCode;

/**
 * 状态机守卫中的操作者类别。
 *
 * <p>SM-CONSULT-001 的"角色"列只出现员工、工程师和系统三种。
 * 系统不是 DM-002 的 RoleCode,而是 EV-001 的 actor_type=SYSTEM,
 * 因此单独建模;PLATFORM_ADMIN/KNOWLEDGE_ADMIN 不在咨询迁移表中出现,
 * 按 SM-001"任何未列出的组合均拒绝"处理。
 */
public enum Actor {

    EMPLOYEE,
    ENGINEER,
    SYSTEM;

    /** 角色到操作者类别的映射;不参与咨询迁移的角色返回 null。 */
    public static Actor of(RoleCode role) {
        if (role == null) {
            return null;
        }
        return switch (role) {
            case EMPLOYEE -> EMPLOYEE;
            case ENGINEER -> ENGINEER;
            case PLATFORM_ADMIN, KNOWLEDGE_ADMIN -> null;
        };
    }
}
