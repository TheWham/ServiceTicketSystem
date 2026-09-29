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

    /** 系统主体,供调度任务使用(EV-001 actor_type=SYSTEM)。 */
    public static CurrentUser system() {
        return new CurrentUser("SYSTEM", null, Actor.SYSTEM);
    }
}
