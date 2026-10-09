package com.itticket.user.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import lombok.Data;

/** 主管修改用户角色（admin_only）。reason 选填，用于审计追溯 */
@Data
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public class ChangeRoleRequest {
    /** 新角色：EMPLOYEE/ENGINEER/PLATFORM_ADMIN/KNOWLEDGE_ADMIN（兼容 KB_ADMIN） */
    @JsonAlias("roleCode")
    private String roleCode;
    /** 变更原因（选填，审计追溯用） */
    private String reason;
}
