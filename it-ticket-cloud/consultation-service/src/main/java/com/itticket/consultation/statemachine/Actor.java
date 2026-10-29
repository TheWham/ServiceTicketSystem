package com.itticket.consultation.statemachine;

import com.itticket.consultation.enums.RoleCode;

/**
 * 状态机守卫中的操作者类别。
 *
 * <p>SM-CONSULT-001 的"角色"列只出现员工、工程师和系统三种。
 * 系统不是 DM-002 的 RoleCode,而是 EV-001 的 actor_type=SYSTEM,因此单独建模。
 *
 * <p>员工角色代表咨询的"发起方"。平台管理员与知识库管理员同样需要使用自助智能客服，
 * 因此在本状态机中被视为发起方(Actor.EMPLOYEE),与员工共享同一套起点与员工侧动作。
 * 工程师仍然是独立的"处理方"。无匹配角色返回 null。
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
            case EMPLOYEE, PLATFORM_ADMIN, KNOWLEDGE_ADMIN -> EMPLOYEE;
            case ENGINEER -> ENGINEER;
        };
    }
}
