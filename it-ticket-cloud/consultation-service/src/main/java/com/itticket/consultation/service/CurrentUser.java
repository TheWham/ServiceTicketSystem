package com.itticket.consultation.service;

import com.itticket.consultation.enums.RoleCode;
import com.itticket.consultation.statemachine.Actor;

/** 已解析的认证主体。userId 来自网关透传的认证上下文,不信任请求体中的操作者 ID(AI-002、AX-001)。 */
public record CurrentUser(String userId, RoleCode role, Actor actor) {

    public boolean isEmployee() {
        return role == RoleCode.EMPLOYEE;
    }

    public boolean isEngineer() {
        return role == RoleCode.ENGINEER;
    }

    public boolean isPlatformAdmin() {
        return role == RoleCode.PLATFORM_ADMIN;
    }

    /**
     * 自助智能客服的发起方:员工与平台/知识库管理员共用员工侧动作(Actor.EMPLOYEE)。
     * 与 {@link #isEmployee()} 的区别是这里包含被映射到发起方的管理员角色。
     */
    public boolean isConsultationRequester() {
        return actor == Actor.EMPLOYEE;
    }

    /** 系统主体,供调度任务使用(EV-001 actor_type=SYSTEM)。 */
    public static CurrentUser system() {
        return new CurrentUser("SYSTEM", null, Actor.SYSTEM);
    }
}
